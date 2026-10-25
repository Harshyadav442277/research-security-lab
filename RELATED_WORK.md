# Reading connections and attribution

These notes identify methodological connections. No external code or dataset is incorporated, and neither paper's results have been reproduced here.

## KernJC, RAID 2024

Bonan Ruan, Jiahao Liu, Chuqi Zhang and Zhenkai Liang, [KernJC: Automated Vulnerable Environment Generation for Linux Kernel Vulnerabilities](https://arxiv.org/html/2404.11107v2). Preparation reading covered the introduction, version/configuration identification, evaluation and discussion.

The paper separates constructing an environment that contains and exposes a vulnerability from triggering it. Patch checks address inaccurate version labels; configuration analysis addresses hidden prerequisites. Its discussion distinguishes reproduction from exploitability. The useful lesson for this much smaller lab is to record the executable environment and policy configuration alongside each observed outcome. Its Linux-kernel technique and evaluation are separate work; this lab does not implement them.

## Forky, ICSE 2025

Won Hoi Kim et al., [Fork State-Aware Differential Fuzzing for Blockchain Consensus Implementations](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/145/Fork-State-Aware-Differential-Fuzzing-for-Blockchain-Consensus-Implementations). Preparation reading was limited to the official conference abstract and author list; the full paper was unavailable through the attempted author-hosted links.

The abstract motivates comparing implementation behavior across fork states because ordinary coverage can miss relevant distinctions. The broad connection is to exposing state-dependent behavior and comparing outcomes. This lab does not implement fork exploration, a consensus protocol, differential fuzzing or Forky's feedback mechanism.

## Standard-library implementation references

Python [http.server](https://docs.python.org/3/library/http.server.html), [hmac](https://docs.python.org/3/library/hmac.html) and [urllib.parse](https://docs.python.org/3/library/urllib.parse.html) describe the transport, authentication primitive and URL parser used here. In particular, the HTTP server is an experiment transport, not a recommended production deployment.
