"""Run real loopback HTTP experiments and emit portable outcome evidence."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import platform
import random
import socket
import sys
import threading

from policy import KEYS, MAX_BODY, Policy, encode, sign
from server import make_server

NOW = 1800000000


def request(i="r1", **changes):
    value = dict(request_id=i, timestamp=NOW, tool="emit", resource="device-a",
                 url="https://telemetry.example.test/ingest", value="temperature=21")
    value.update(changes)
    return encode(value)


@contextmanager
def running(policy):
    server = make_server(policy)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def send(port, raw, key="alice", signature=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        actual = {"Content-Type": "application/json", "X-Key-Id": key,
                  "X-Signature": sign(raw, key) if signature is None else signature}
        actual.update(headers or {})
        connection.request("POST", "/execute", body=raw, headers=actual)
        response = connection.getresponse()
        reason = json.loads(response.read())["reason"]
        return f"{response.status}:{reason}"
    finally:
        connection.close()


def run(seed, repetitions):
    rows = []

    def record(name, observed, expected, effects, expected_effects):
        good = Counter(observed) == Counter(expected) and effects == expected_effects
        rows.append(dict(name=name, observed=dict(sorted(Counter(observed).items())),
                         expected=dict(sorted(Counter(expected).items())), effects=effects,
                         expected_effects=expected_effects, passed=good))

    def case(name, raw, expected, disabled=(), signature=None, key="alice", headers=None):
        policy = Policy(clock=lambda: NOW, disabled=disabled)
        with running(policy) as port:
            observed = [send(port, raw, key, signature, headers)]
        record(name, observed, [expected], len(policy.effects), int(expected == "200:accepted"))

    case("valid", request(), "200:accepted")
    case("valid_explicit_port", request(url="https://telemetry.example.test:443/ingest"), "200:accepted")
    case("tampered_signature", request(), "401:authentication", signature="0" * 64)
    case("non_ascii_signature", request(), "401:authentication", signature="\u00e9" * 64)
    case("forged_key_id", request(), "401:authentication", key="unknown", signature="0" * 64)
    case("cross_device", request(resource="device-b"), "403:scope")
    case("cross_device_without_scope", request(resource="device-b"), "200:accepted", disabled={"scope"})
    case("unknown_tool", request(tool="shell"), "403:tool")
    case("bad_json", b'{"request_id":', "400:schema")
    case("non_object", b'[]', "400:schema")
    case("duplicate_json_key", request()[:-1] + b',"tool":"emit"}', "400:schema")
    case("boolean_timestamp", request(timestamp=True), "400:schema")
    case("oversized_integer_timestamp", request(timestamp=10 ** 1000), "400:schema")
    case("invalid_utf8", b'\xff', "400:schema")
    case("oversize", b'x' * (MAX_BODY + 1), "413:body_size")
    case("wrong_content_type", request(), "415:content_type", headers={"Content-Type": "text/plain"})
    case("stale", request(timestamp=NOW - 31), "403:freshness")
    case("future", request(timestamp=NOW + 31), "403:freshness")
    case("stale_without_freshness", request(timestamp=NOW - 31), "200:accepted", disabled={"freshness"})
    urls = ["http://telemetry.example.test/ingest", "https://127.0.0.1/ingest",
            "https://169.254.169.254/ingest", "https://telemetry.example.test.evil.test/ingest",
            "https://telemetry.example.test@evil.test/ingest", "https://telemetry.example.test:444/ingest",
            "https://telemetry.example.test/ingest#fragment", "https://telemetry.example.test/redirect?to=x",
            "https://telemetry.example.test\\@evil.test/ingest", "https://telemetry.example.test:bad/ingest",
            "https://telemetry.example.test/\ningest"]
    for i, url in enumerate(urls):
        case(f"url_{i:02d}", request(url=url), "403:url")
    case("url_without_gate", request(url="https://127.0.0.1/ingest"), "200:accepted", disabled={"url"})

    for name, extra in (
            ("duplicate_length", b"Content-Length: 0\r\nContent-Length: 0\r\n"),
            ("chunked_framing", b"Transfer-Encoding: chunked\r\nContent-Length: 0\r\n"),
            ("negative_length", b"Content-Length: -1\r\n")):
        policy = Policy(clock=lambda: NOW)
        with running(policy) as port:
            with socket.create_connection(("127.0.0.1", port), timeout=8) as client:
                client.sendall(b"POST /execute HTTP/1.1\r\nHost: localhost\r\n" + extra + b"\r\n")
                response = b""
                while chunk := client.recv(4096):
                    response += chunk
                body = json.loads(response.split(b"\r\n\r\n", 1)[1])
                observed = [response.split(b" ", 2)[1].decode() + ":" + body["reason"]]
        record(name, observed, ["400:framing"], len(policy.effects), 0)

    for disabled in ((), {"replay"}):
        policy = Policy(clock=lambda: NOW, disabled=disabled)
        with running(policy) as port:
            values = [send(port, request()) for _ in range(2)]
        expected = ["200:accepted"] * 2 if disabled else ["200:accepted", "409:replay"]
        record("replay_disabled" if disabled else "sequential_replay", values, expected,
               len(policy.effects), 2 if disabled else 1)

    for disabled in ((), {"rate"}):
        policy = Policy(clock=lambda: NOW, disabled=disabled)
        with running(policy) as port:
            values = [send(port, request(f"r{i}")) for i in range(4)]
        expected = ["200:accepted"] * 4 if disabled else ["200:accepted"] * 3 + ["429:rate"]
        record("rate_disabled" if disabled else "rate_limit", values, expected,
               len(policy.effects), 4 if disabled else 3)

    rng = random.Random(seed)
    for trial in range(repetitions):
        for disabled in ((), {"replay", "rate"}):
            policy = Policy(clock=lambda: NOW, disabled=disabled)
            barrier = threading.Barrier(8)
            def concurrent_send(_):
                barrier.wait(timeout=8)
                return send(port, request(f"concurrent{trial}"))
            order = list(range(8))
            rng.shuffle(order)
            with running(policy) as port:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    values = list(pool.map(concurrent_send, order))
            expected = ["200:accepted"] * 8 if disabled else ["200:accepted"] + ["409:replay"] * 7
            record(f"concurrent_{'disabled' if disabled else 'atomic'}_{trial:02d}", values,
                   expected, len(policy.effects), 8 if disabled else 1)

    # Temporal boundaries and principal isolation, under the experiment clock.
    clock = [NOW]
    policy = Policy(clock=lambda: clock[0])
    with running(policy) as port:
        values = [send(port, request("futureedge", timestamp=NOW + 30))]
        clock[0] += 60
        values.append(send(port, request("futureedge", timestamp=NOW + 30)))
        clock[0] += 1
        values.append(send(port, request("futureedge", timestamp=NOW + 30)))
    record("future_nonce_retention", values, ["200:accepted", "409:replay", "403:freshness"],
           len(policy.effects), 1)
    clock[0] = NOW
    policy = Policy(clock=lambda: clock[0])
    with running(policy) as port:
        values = [send(port, request(f"rate{i}")) for i in range(4)]
        clock[0] += 2
        values.append(send(port, request("rate3", timestamp=NOW + 2)))
        values.append(send(port, request("rate3", timestamp=NOW + 2, resource="device-b"), key="bob"))
    record("rate_recovery_and_principal_isolation", values,
           ["200:accepted"] * 3 + ["429:rate", "200:accepted", "200:accepted"], len(policy.effects), 5)

    # Deliberately measure a known limitation: process restart erases replay state.
    values = []
    effects = 0
    for _ in range(2):
        policy = Policy(clock=lambda: NOW)
        with running(policy) as port:
            values.append(send(port, request("restart")))
        effects += len(policy.effects)
    record("known_limitation_restart_replay", values, ["200:accepted"] * 2, effects, 2)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("results/latest.json"))
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 100:
        parser.error("repetitions must be between 1 and 100")
    rows = run(args.seed, args.repetitions)
    files = ("policy.py", "server.py", "ledger.py", "run_experiments.py")
    hashes = {f: hashlib.sha256(Path(__file__).with_name(f).read_bytes()).hexdigest() for f in files}
    data = dict(schema_version=1, python=sys.version.split()[0], platform=platform.platform(),
                seed=args.seed, repetitions=args.repetitions, logical_time=NOW, source_sha256=hashes,
                passed=sum(r["passed"] for r in rows), total=len(rows), scenarios=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    table = ["# Measured experiment outcomes", "", "Known-limit and ablation rows pass when the deliberately weak behavior is observed.", "",
             "| Scenario | Observed HTTP outcomes | Recorded effects | Expected effects | Match |", "|---|---|---:|---:|---|"]
    for row in rows:
        outcomes = ", ".join(f"{k} x{v}" for k, v in row["observed"].items())
        table.append(f"| {row['name']} | {outcomes} | {row['effects']} | {row['expected_effects']} | {'yes' if row['passed'] else 'NO'} |")
    args.output.with_suffix(".md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"{data['passed']}/{data['total']} scenarios matched; evidence: {args.output}")
    return 0 if data["passed"] == data["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
