# HTTP replay and policy experiments

Small Python lab for testing signed requests, replay checks and device permissions over HTTP. The main comparison is simple: send the same request eight times at once, then count how many actions the server records.

The server only records actions in a list. It doesn't contact a device, fetch a URL or send an MQTT message.

## Run the experiments

No packages to install. Use Python 3.10 or newer:

```sh
python run_experiments.py
```

The default run should report `60/60 scenarios matched` and write `results/latest.json` and `results/latest.md`. The committed runs are from Windows (Python 3.12.2) and Ubuntu under WSL (Python 3.14.4). Each JSON report records the environment and hashes of the three experiment source files.

`60/60` means the observations matched the expected results. Some cases deliberately remove a check, and one demonstrates replay after a restart. It isn't a security score.

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

## Results worth looking at

| Case | With checks | Check removed |
|---|---|---|
| Eight copies arriving together | 1 recorded action | 8 without replay and rate checks |
| Alice targeting Bob's device | Rejected | Recorded without scope check |
| Four requests inside two seconds | 3 recorded actions | 4 without rate check |
| Same request after restart | Accepted again | Replay state is lost |

The concurrent comparison runs ten times. A barrier starts the clients together, but the OS still chooses the actual schedule. The seed changes dispatch order, not thread interleavings.

See the [Windows results](results/windows.md), [Linux results](results/linux.md) and [experiment notes](RESEARCH_NOTE.md) for the details. [EXPLAIN.md](EXPLAIN.md) lists the parts of the code worth tracing; [RELATED_WORK.md](RELATED_WORK.md) has the reading references.

## Limits

This only tests a single service process and an in-memory recording sink. It doesn't test durable delivery, TLS, DNS rebinding or redirects. `http.server` is used as a local experiment transport, not a production deployment.

A Dockerfile is included, but its build and execution are unverified because the preparation host's Docker engine was unavailable. Native Windows and WSL runs were checked.

Implementation and documentation were prepared with AI assistance. This is a learning project, with no claim of research novelty or independent reproduction of the linked papers.
