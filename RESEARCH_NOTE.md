# Experiment notes

The useful observation here is the number of recorded actions, not just the HTTP status. Eight duplicate requests can all look reasonable individually while still causing the same action eight times. The first version used a list; the follow-up adds a local SQLite journal to test what changes across process boundaries.

## Setup

Requests are signed with HMAC-SHA256 using public fixture keys. The server checks the exact request bytes, JSON schema, tool name, resource permission and URL string. Freshness, replay admission, rate admission and the recording action happen under the same lock.

The runner sends actual HTTP requests over loopback. It uses a fixed logical clock for the boundary cases and an eight-worker barrier for concurrent delivery. It checks both response counts and the length of the recording list. Weakened variants are passed directly to `Policy`; there is no HTTP option to disable a check.

## What the runs showed

The refreshed in-memory runs matched all 61 expected cases on Windows and Ubuntu. They contain the same observations and source hashes, despite using different Python versions and operating systems. The added case rejects a 1,001-digit integer timestamp, which could otherwise raise an overflow error during the floating-point freshness calculation.

1. With the lock and replay check, each concurrent trial recorded one action for eight copies. Removing replay and rate checks recorded eight.
2. A rate-limited request could retry after the two-second window. Rejected requests did not consume their request ID.
3. A request dated 30 seconds into the future was still rejected as a duplicate 60 seconds later. This is why nonce retention is 61 seconds, rather than 30.
4. Creating a fresh server admitted the same request again. The replay guarantee only lasts for the life of one `Policy` instance.

The URL tests only check strings. There is no DNS resolution or fetch, so a rejection of a metadata-address URL doesn't establish resistance to SSRF in a real HTTP client.

## A Windows issue during setup

An early oversized-body case returned `ConnectionAbortedError` instead of the expected HTTP rejection. The server closed a connection with unread request data. Flushing the response and shutting down the write side before closing fixed that case on the tested Windows host. The framing and oversized-body cases remain in the runner.

## SQLite follow-up

`ledger.py` uses `BEGIN IMMEDIATE` before reading replay and rate state. One inserted action row supplies both the journal record and the state for later admission checks. The timestamp is read after acquiring the writer, so time spent waiting for it doesn't make an old freshness decision look current.

The ten cases in `run_persistence.py` matched on Windows (SQLite 3.43.1) and Ubuntu (SQLite 3.46.1). These include shared replay/rate admission in two independently spawned server processes and a database-lock failure that returns 503 without forgetting previous state.

For crash injection, a child process runs the real admission and INSERT path with a connection subclass whose `commit()` exits the process. Exiting before the real commit leaves zero actions; a retry records one. Exiting after the real commit leaves one action; a retry is rejected. This targets two known process-exit points, not arbitrary disk corruption, power loss or a crash during every SQLite write.

The [Windows](results/persistence/windows.md) and [Linux](results/persistence/linux.md) tables include exit codes, action counts before retry and retry outcomes. The JSON files include SQLite versions and all five relevant source hashes. Temporary files are removed after the run; `.state/` is ignored for manual experiments.

## Remaining questions

The journal and an external network action would be separate commits. Deduplicating a local row doesn't solve the crash window between those two systems. An outbox experiment could explore that boundary next.

No throughput, power-loss, clock-jump or network-filesystem benchmark was run. Database history is retained without compaction. These results cover only the listed local experiments, and the GitHub workflow records the separate container smoke-test status.
