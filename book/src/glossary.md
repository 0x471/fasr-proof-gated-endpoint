# Glossary

## The system

| Term | Meaning |
|---|---|
| Endpoint | The Raspberry Pi running checking software between the AI server and the outside world. |
| Proof, or zero-knowledge proof | Short evidence that a specific computation produced a specific output. It can be checked quickly without repeating the computation. |
| Proof-system soundness | The assumption that the proof system resists false computation claims. This project does not assess it. |
| Bundle | Approved model settings, verification key and public setup file. Each file is pinned by hash. |
| Hash or pin | A file fingerprint. Pinning means refusing to run if a file differs from the approved fingerprint. |
| Verification key, vk | Public data that lets anyone check proofs for the approved model's circuit. It is not a signing key. |
| SRS | The proof system's public setup file, pinned like the other bundle files. |
| Request binding | Connecting the proof to the endpoint's question, approved model and interpretation of output. |
| EZKL | The tool proving and checking our small model. Its source is public. Pinned release 23.0.5 has no licence file; the Apache-2.0 licence was removed in January 2024. |
| Parser | Code that reads an incoming message according to its format. |
| Fuzzing | Testing parsers with random and corrupted messages; accepted messages must re-encode identically. This is not a timing experiment. |
| TPM | A hardware component whose counter is planned to prevent restoring an older update store. That protection is not built yet. |

## Answers and release

| Term | Meaning |
|---|---|
| Release rule, or policy | When replies leave: immediately, in arrival order, or at a fixed time. |
| Arrival order | Each reply follows all earlier questions' replies. This removes the server's choice of order. |
| Deadline or budget | How long the endpoint allows for a valid answer before returning `unavailable`. Under fixed release, it also sets the earliest release time. |
| Fixed-time release | Replies follow arrival order and never leave before their set time. It promises no latest time. It hides most server timing at a latency cost; a trace remained without spin. Actual lateness is in [Measurements](results.md). |
| Spin | Waking early and busy-waiting until the release time. |
| Replay | Reusing an old valid answer. No pending question receives two replies, but a new question with the same encoding can accept an old proof. For one deterministic model this gives no output choice; it does not prove fresh computation. |
| `unavailable` | The single server-related error reply. It omits the cause so error text cannot carry the server's message. |

## Leakage and statistics

| Term | Meaning |
|---|---|
| Bit | One yes/no choice; 16 bits can hold two text letters. Rates here are bits per answer or second. |
| Channel | A way to convey information outside: timing, order, failures, packet sizes or logs. |
| Side channel | Information carried outside content: when, in what order or whether something happens. |
| Residual | Leakage remaining after a defence; here, the sub-millisecond trace under fixed release. |
| Permutation test | Shuffle planted labels thousands of times. The p-value is the fraction producing a difference at least as large as the observed one. |
| Held-out decoder | Fit a threshold on half the answers, test on the other half, then swap. The null test refits on each label shuffle. |
| Mutual information | Here, how many bits the binned arrival time reveals about the planted bit, against shuffled labels. It describes that statistic, not a leakage bound. |
| Honest control | Repeat the analysis while the server hides nothing. Any apparent signal is noise. |

## Versions

- v0: Python endpoint on the standard Pi system.
- v1: Rust endpoint on a stripped, read-only system, with stricter release rules, failure cap, sandboxed checker and signed updates.
- v2, planned: secure boot, two physical ports, a counter against restoring old update stores and signed images.
