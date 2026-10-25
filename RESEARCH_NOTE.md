# Admission checks under concurrent duplicate delivery

## Problem

A rejected request and an absent action are different observations. Can a small, repeatable HTTP experiment show both the admission decision and the number of actions recorded when security checks interact?

## Failure model

The sender can submit malformed traffic, alter authentication headers, replay signed requests, send concurrent duplicates and use its own valid credential against an unauthorized resource. The service, clock fixture and experiment runner are trusted. Keys are public synthetic fixtures. This models policy logic under controlled delivery, rather than cryptographic key theft or a hostile host.

## Setup and measurements

A standard-library Python HTTP server authenticates the exact request bytes with HMAC-SHA256, validates a strict schema and checks tool, device and URL policy. A lock covers freshness, nonce admission, rate admission and insertion into a recording sink. Independent HTTP connections exercise the service. No external system receives traffic.

The runner records response counts and actual recording-list lengths against explicit expected outcomes. It compares the full policy to weakened variants, repeats eight-client duplicate delivery ten times and advances a logical clock through rate and freshness boundaries. Source hashes and environment metadata accompany the evidence.

## Results

Both native Windows and Ubuntu under WSL matched all 60 expected scenario outcomes. In each concurrent trial, the full policy recorded one action for eight copies. With replay and rate checks removed, the same workload recorded eight. Scope, freshness, rate and URL ablations each admitted the violation that their corresponding full-policy case rejected. Rejected malformed and unauthenticated inputs recorded no action.

One intentionally measured limitation is important: recreating the service admits the same still-fresh request again because replay memory is lost. An outcome match in that case records the weakness; it is not a successful defense.

## Limits

This is a synthetic admission experiment, not a reproduction of a published system or a security benchmark. The sink has no external effects. TLS, DNS, redirects, broker behavior, crash consistency, multiple service processes and hardware remain outside its scope. Scheduling is uncontrolled; timing and throughput are not benchmarked. Docker files exist, but container execution is unverified. Passing the corpus does not prove absence of other bugs.

## Next experiment

Replace the recording sink and nonce state with one transactional durable ledger. Repeat the duplicate workload across two server processes and forced restarts. Specify the point at which an action becomes durable before claiming delivery semantics.
