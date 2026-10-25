# HTTP replay and policy experiments

Small Python lab for testing signed requests, replay checks and device permissions over HTTP. The main comparison is simple: send the same request eight times at once, then count how many actions the server records.

The default server records actions in a list. An optional SQLite journal keeps admission state and recorded actions across restarts and shares them between local server processes. Neither mode contacts a device, fetches a URL or sends an MQTT message.

## Run the experiments

No packages to install. Use Python 3.10 or newer:

```sh
python run_experiments.py
```

The default run should report `61/61 scenarios matched` and write `results/latest.json` and `results/latest.md`. The committed runs are from Windows (Python 3.12.2) and Ubuntu under WSL (Python 3.14.4). Each JSON report records the environment and hashes of the four experiment source files.

`61/61` means the observations matched the expected results. Some cases deliberately remove a check, and one demonstrates replay after a restart. It isn't a security score.

## Try a request by hand

Start the server in one terminal:

```sh
python server.py
```

In another terminal, run these two commands within 30 seconds:

```sh
python send_request.py --request-id demo1
python send_request.py --request-id demo1
```

The first should print `200 accepted`, and the second `409 replay`. Restart the server and send it again: it gets accepted because the replay state was only in memory.

To try a permission failure:

```sh
python send_request.py --resource device-b
# 403 scope: the default Alice key only has access to device-a
```

The client exits with 0 for an accepted request, 1 for a rejection and 2 for a connection/response error. Keys are public test fixtures in `policy.py`. Both server and client connect only over loopback; the request's `url` field is just input to the policy check.

## Keep state across restarts

Stop the default server, then start it with a database file:

```sh
python server.py --database .state/lab.sqlite3
```

Run the same two client commands above. Now restarting the server with that same file keeps rejecting a reused ID while its replay entry is live. Starting another server with `--port 8081` and the same database shares the replay and rate limits.

The persistence experiment handles temporary databases, two child server processes and crash injection:

```sh
python run_persistence.py
# 10/10 persistence scenarios matched
```

It checks a crash immediately before commit and immediately after commit but before a response. The former leaves no action, so retry succeeds. The latter leaves one action, so retry is rejected. A locked database returns `503 storage_unavailable`; there is no fallback to an empty memory cache.

See the measured [Windows](results/persistence/windows.md) and [Linux](results/persistence/linux.md) outcomes. These tests cover local database rows, not an external action committed in another system.

## Results worth looking at

| Case | With checks | Check removed |
|---|---|---|
| Eight copies arriving together | 1 recorded action | 8 without replay and rate checks |
| Alice targeting Bob's device | Rejected | Recorded without scope check |
| Four requests inside two seconds | 3 recorded actions | 4 without rate check |
| Same request after restart, in-memory mode | Accepted again | Replay state is lost |
| Same request after restart, SQLite mode | Rejected while nonce is live | State kept in the database |

The concurrent comparison runs ten times. A barrier starts the clients together, but the OS still chooses the actual schedule. The seed changes dispatch order, not thread interleavings.

See the [Windows results](results/windows.md), [Linux results](results/linux.md) and [experiment notes](RESEARCH_NOTE.md) for the details. [EXPLAIN.md](EXPLAIN.md) lists the parts of the code worth tracing; [RELATED_WORK.md](RELATED_WORK.md) has the reading references.

## Limits

The SQLite mode tests two processes on one host, with a local database file and a 61-second replay entry lifetime. It retains action rows, so the file grows with the experiment. This does not establish exactly-once delivery to an external service, power-loss recovery, network-filesystem safety, TLS, DNS rebinding or redirect handling. `http.server` is a local experiment transport, not a production deployment.

GitHub Actions runs both experiments on Windows and Linux, stores their result files for seven days, and smoke-tests both runners in Docker on Linux. Action versions are pinned by commit. The [workflow](.github/workflows/experiments.yml) is the source for these checks; inspect the [run results](https://github.com/Harshyadav442277/research-security-lab/actions) for their actual status. The preparation host's Docker engine was unavailable.

Implementation and documentation were prepared with AI assistance. This is a learning project, with no claim of research novelty or independent reproduction of the linked papers.
