# Experiment notes

The useful observation here is the number of recorded actions, not just the HTTP status. Eight duplicate requests can all look reasonable individually while still causing the same action eight times.

## Setup

Requests are signed with HMAC-SHA256 using public fixture keys. The server checks the exact request bytes, JSON schema, tool name, resource permission and URL string. Freshness, replay admission, rate admission and the recording action happen under the same lock.

The runner sends actual HTTP requests over loopback. It uses a fixed logical clock for the boundary cases and an eight-worker barrier for concurrent delivery. It checks both response counts and the length of the recording list. Weakened variants are passed directly to `Policy`; there is no HTTP option to disable a check.

## What the runs showed

Both committed runs matched all 60 expected cases. They contain the same observations and source hashes, despite using different Python versions and operating systems.

1. With the lock and replay check, each concurrent trial recorded one action for eight copies. Removing replay and rate checks recorded eight.
2. A rate-limited request could retry after the two-second window. Rejected requests did not consume their request ID.
3. A request dated 30 seconds into the future was still rejected as a duplicate 60 seconds later. This is why nonce retention is 61 seconds, rather than 30.
4. Creating a fresh server admitted the same request again. The replay guarantee only lasts for the life of one `Policy` instance.

The URL tests only check strings. There is no DNS resolution or fetch, so a rejection of a metadata-address URL doesn't establish resistance to SSRF in a real HTTP client.

## A Windows issue during setup

An early oversized-body case returned `ConnectionAbortedError` instead of the expected HTTP rejection. The server closed a connection with unread request data. Flushing the response and shutting down the write side before closing fixed that case on the tested Windows host. The framing and oversized-body cases remain in the runner.

## Next useful change

The main missing piece is persistence. A useful follow-on experiment would store request IDs and actions in one transaction, then repeat the duplicate workload across restarts and two service processes. Recording a nonce before an external action is not enough to establish exactly-once delivery if the process can crash between them.

No throughput or scheduling benchmark was run. The sink is still a list, the clocks are controlled, and the container route has not been checked. The committed results cover the listed cases only.
