# Reading references

## KernJC (RAID 2024)

Bonan Ruan, Jiahao Liu, Chuqi Zhang and Zhenkai Liang, [KernJC: Automated Vulnerable Environment Generation for Linux Kernel Vulnerabilities](https://arxiv.org/html/2404.11107v2).

KernJC treats the environment needed to expose a vulnerability as part of the reproduction problem. Its patch and configuration analysis is a different task from this lab. The relevant lesson here is to retain the source and configuration alongside an observed result. The preparation notes used its introduction, method, evaluation and discussion; no kernel experiments were reproduced.

## Forky (ICSE 2025)

Won Hoi Kim et al., [Fork State-Aware Differential Fuzzing for Blockchain Consensus Implementations](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/145/Fork-State-Aware-Differential-Fuzzing-for-Blockchain-Consensus-Implementations).

Only the official conference abstract and author list were available during preparation. It describes comparing implementation behavior across fork states. This lab has no consensus implementation, fork exploration or Forky feedback mechanism.

## Python documentation

1. [http.server](https://docs.python.org/3/library/http.server.html), the local test transport and its deployment limitations.
2. [hmac](https://docs.python.org/3/library/hmac.html), signing request bytes and comparing digests.
3. [urllib.parse](https://docs.python.org/3/library/urllib.parse.html), parsing the URL field. Parsing alone does not validate a network destination.
