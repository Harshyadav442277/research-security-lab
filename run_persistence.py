"""Measure restart, process-sharing and commit-boundary behavior of the ledger."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import argparse
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import sqlite3
import sys
from tempfile import TemporaryDirectory
import threading
from unittest.mock import patch

from ledger import SQLiteLedger
from policy import Policy
from run_experiments import NOW, request, running, send
from server import make_server


def serve_worker(database, ready, stop):
    try:
        with make_server(Policy(clock=lambda: NOW, ledger=SQLiteLedger(database))) as server:
            server.timeout = 0.05
            ready.put({"port": server.server_port, "pid": os.getpid()})
            while not stop.is_set():
                server.handle_request()
    except Exception as error:
        ready.put({"error": repr(error)})
        raise


@contextmanager
def two_servers(database):
    SQLiteLedger(database)
    context = multiprocessing.get_context("spawn")
    ready = context.Queue()
    stop = context.Event()
    children = [context.Process(target=serve_worker, args=(database, ready, stop)) for _ in range(2)]
    try:
        for child in children:
            child.start()
        workers = [ready.get(timeout=20) for _ in children]
        if any("error" in worker for worker in workers):
            raise RuntimeError(workers)
        if len({worker["pid"] for worker in workers}) != 2:
            raise RuntimeError("Expected two different server processes")
        yield [worker["port"] for worker in workers]
    finally:
        stop.set()
        for child in children:
            if child.pid is not None:
                child.join(timeout=5)
                if child.is_alive():
                    child.terminate()
                    child.join(timeout=5)
        ready.close()
        ready.join_thread()
    if any(child.exitcode != 0 for child in children):
        raise RuntimeError(f"Server process failed: {[child.exitcode for child in children]}")


def crash_worker(database, after_commit):
    # Fault injection is confined to this short-lived experiment process.
    # The real admission/INSERT path runs; only Connection.commit is changed.
    real_connect = sqlite3.connect

    class CrashConnection(sqlite3.Connection):
        def commit(self):
            if after_commit:
                super().commit()
            os._exit(74 if after_commit else 73)

    def connect(*args, **kwargs):
        return real_connect(*args, **kwargs, factory=CrashConnection)

    with patch("ledger.sqlite3.connect", new=connect):
        policy = Policy(clock=lambda: NOW, ledger=SQLiteLedger(database))
        raw = request("crash")
        from policy import sign
        policy.execute(raw, "alice", sign(raw))


def run():
    rows = []

    def record(name, observed, expected, ledger, expected_effects):
        effects = len(ledger.effects)
        rows.append(dict(name=name, observed=dict(sorted(Counter(observed).items())),
                         expected=dict(sorted(Counter(expected).items())), effects=effects,
                         expected_effects=expected_effects,
                         passed=Counter(observed) == Counter(expected) and effects == expected_effects))

    with TemporaryDirectory(prefix="policy-ledger-") as directory:
        root = Path(directory)
        ledger = SQLiteLedger(root / "restart.sqlite3")
        values = []
        for _ in range(2):
            # Reconstruct both policy and ledger; no Python cache is reused.
            policy = Policy(clock=lambda: NOW, ledger=SQLiteLedger(ledger.path))
            with running(policy) as port:
                values.append(send(port, request("restart")))
        record("restart_keeps_replay_state", values, ["200:accepted", "409:replay"], ledger, 1)

        ledger = SQLiteLedger(root / "changed-body.sqlite3")
        with running(Policy(clock=lambda: NOW, ledger=ledger)) as port:
            values = [send(port, request("same-id", value=value)) for value in ("original", "changed")]
        values.append("stored:" + ledger.effects[0]["value"])
        record("same_id_changed_body", values, ["200:accepted", "409:replay", "stored:original"], ledger, 1)

        clock = [NOW]
        ledger = SQLiteLedger(root / "rate.sqlite3")
        with running(Policy(clock=lambda: clock[0], ledger=ledger)) as port:
            values = [send(port, request(f"rate{i}")) for i in range(4)]
            values.append(send(port, request("rate0", resource="device-b"), key="bob"))
        # The rate budget, as well as replay IDs, must survive a restart.
        with running(Policy(clock=lambda: clock[0], ledger=SQLiteLedger(ledger.path))) as port:
            values.append(send(port, request("rate3")))
            clock[0] += 2
            values.append(send(port, request("rate3", timestamp=NOW + 2)))
        record("rate_restart_recovery_and_principals", values,
               ["200:accepted"] * 3 + ["429:rate", "200:accepted", "429:rate", "200:accepted"], ledger, 5)

        clock[0] = NOW
        ledger = SQLiteLedger(root / "expiry.sqlite3")
        with running(Policy(clock=lambda: clock[0], ledger=ledger)) as port:
            values = [send(port, request("expiry", timestamp=NOW + 30))]
            clock[0] += 60
            values.append(send(port, request("expiry", timestamp=NOW + 30)))
            clock[0] += 1
            values.append(send(port, request("expiry", timestamp=NOW + 61)))
        record("nonce_retention_and_id_reuse", values,
               ["200:accepted", "409:replay", "200:accepted"], ledger, 2)

        for duplicate in (True, False):
            ledger = SQLiteLedger(root / f"processes-{duplicate}.sqlite3")
            barrier = threading.Barrier(8)
            with two_servers(str(ledger.path)) as ports:
                def worker(i):
                    barrier.wait(timeout=10)
                    return send(ports[i % 2], request("shared" if duplicate else f"request{i}"))
                with ThreadPoolExecutor(max_workers=8) as pool:
                    values = list(pool.map(worker, range(8)))
            record("two_process_duplicate" if duplicate else "two_process_rate", values,
                   ["200:accepted"] + ["409:replay"] * 7 if duplicate else ["200:accepted"] * 3 + ["429:rate"] * 5,
                   ledger, 1 if duplicate else 3)

        for after_commit in (False, True):
            ledger = SQLiteLedger(root / f"crash-{after_commit}.sqlite3")
            context = multiprocessing.get_context("spawn")
            child = context.Process(target=crash_worker, args=(str(ledger.path), after_commit))
            child.start()
            child.join(timeout=20)
            if child.is_alive():
                child.terminate()
                child.join(timeout=5)
                raise RuntimeError("Crash experiment timed out")
            values = [f"child_exit:{child.exitcode}", f"actions_before_retry:{len(ledger.effects)}"]
            with running(Policy(clock=lambda: NOW, ledger=SQLiteLedger(ledger.path))) as port:
                values.append(send(port, request("crash")))
            record("crash_after_commit" if after_commit else "crash_before_commit", values,
                   ["child_exit:74", "actions_before_retry:1", "409:replay"] if after_commit else
                   ["child_exit:73", "actions_before_retry:0", "200:accepted"], ledger, 1)

        ledger = SQLiteLedger(root / "locked.sqlite3", timeout=0.1)
        with running(Policy(clock=lambda: NOW, ledger=ledger)) as port:
            connection = sqlite3.connect(ledger.path, isolation_level=None)
            try:
                connection.execute("BEGIN EXCLUSIVE")
                values = [send(port, request("locked"))]
            finally:
                connection.rollback()
                connection.close()
            values.append(send(port, request("locked")))
        record("locked_database_no_memory_fallback", values,
               ["503:storage_unavailable", "200:accepted"], ledger, 1)

        ledger = SQLiteLedger(root / "rejected.sqlite3")
        with running(Policy(clock=lambda: NOW, ledger=ledger)) as port:
            values = [send(port, b"[]"), send(port, request(resource="device-b")),
                      send(port, request(), signature="0" * 64)]
        record("rejections_do_not_write", values,
               ["400:schema", "403:scope", "401:authentication"], ledger, 0)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/persistence/latest.json"))
    args = parser.parse_args()
    rows = run()
    files = ("policy.py", "server.py", "ledger.py", "run_experiments.py", "run_persistence.py")
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in files}
    data = dict(schema_version=1, python=sys.version.split()[0], platform=platform.platform(),
                sqlite_version=sqlite3.sqlite_version, logical_time=NOW, source_sha256=hashes,
                passed=sum(row["passed"] for row in rows), total=len(rows), scenarios=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    table = ["# SQLite experiment results", "", "These cases measure local recorded actions, not external delivery.", "",
             "| Case | Observed outcomes | Actions | Expected actions | Match |", "|---|---|---:|---:|---|"]
    for row in rows:
        outcomes = ", ".join(f"{key} x{count}" for key, count in row["observed"].items())
        table.append(f"| {row['name']} | {outcomes} | {row['effects']} | {row['expected_effects']} | {'yes' if row['passed'] else 'NO'} |")
    args.output.with_suffix(".md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"{data['passed']}/{data['total']} persistence scenarios matched; evidence: {args.output}")
    return 0 if data["passed"] == data["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
