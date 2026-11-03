# Limitations and open questions

> **In short**
> - Physical separation, secure boot, rollback-resistant storage, on-device update delivery and a hash-chained log are unfinished.
> - Timing capacity, packet signals and the latency trade-off remain unresolved. Load and several-client tests are limited.
> - The results assume a sound proof system, one approved model and no route around the endpoint.

## Not built yet

| Missing part | Why it matters |
|---|---|
| Two physical ports | Both sides share one cable. A second wired port is planned. |
| Secure boot | Permanently writes a key into the board, so needs a spare board. Nothing has been run yet. |
| TPM counter | Prevents restoring a whole older update store. Current rollback checks cannot stop that. |
| Power-loss test on the Pi | Update installation still needs testing on the Pi's file system. |
| Hash-chained log and separate collector | Current logs stay on the device. |
| Real-size proof support | The wire allows at most 64 KiB, sized for the toy model. Attestable's published figures and FlashProve's examples are megabytes. A real prover needs larger frames, more memory per waiting answer and longer release times. |
| On-device update delivery | With no login, updates require a new image or offline access to the card. The card's stored state enforces the same replay and rollback rules offline. |

The [failure cap](leakage.md#what-a-cap-can-do) reduces leakage at a cost in availability. Its bound covers failure patterns only, per boot: restarting resets the in-memory count. Timing needs separate accounting.

## Not settled by measurement

- A capacity bound for arbitrary hiding methods and observers. Planted-bit rates and one binned information statistic are insufficient. Testing the estimator against known synthetic channels does not provide such a bound.
- Load and several clients. One overlapping check per release was not detected; one three-client run was inconclusive. Stacked checks, flooding, longer three-client tests and outside packet captures remain undone.
- Queue pressure. Under fixed release, a state-machine test shows that server choices do not determine which requests get `busy`. Arrival order remains open. The event loop's own delays under load remain an unresolved part of that channel.
- The budget trade-off. Fixed release used 4 s. Honest use of that budget is measured for one and three clients; leakage under other budgets is not.
- The timing trace's cause. Candidates include waking from idle and processor-speed changes under load. The image defaults to the lowest processor speed, which may explain its result; this has not been isolated.

The redesigned spin still needs more data to settle the trace. The existing three-client run does not settle it either. Read the [spin verdict](results.md#what-fixed-release-leaves) and [load results](results.md#load-and-several-clients-on-the-hardened-image-2-nov-protocols-4-and-5) with their conditions.

## What must be trusted

Every server-to-outside path must cross the endpoint. The shared cable does not enforce that physically. We use one pinned model and circuit, with binding specific to EZKL 23.0.5.

The endpoint binary includes EZKL's verifier. Running each check in its own process contains the verifier's crashes and hangs, but the endpoint cannot detect a verifier that wrongly says ACCEPT. On v1, the signed store supplies the model, domain file and release policy, checked at start. Bundle hashes are re-checked for each proof.

The binary relies on the read-only image, and later on v2 secure boot. The Python reference also trusts its interpreter and EZKL command-line tool. [Proof-system soundness](glossary.md) is assumed and outside scope.

The chips and closed boot firmware are trusted; that firmware runs before our code. A backdoored endpoint could release everything. A real deployment needs auditable hardware or endpoints from two vendors in series.

Build machines must be uncompromised. CI builds the binary from pinned sources; a laptop VM builds the image from hash-checked sources and checks it afterwards. Independent builds and v1.1 reproducibility are documented in [Measurements](results.md#attack-surface). Both still trust Buildroot, upstream sources and published hashes; see the [build-machine reference](https://github.com/0x471/fasr-proof-gated-endpoint/blob/main/docs/ATTACK_SURFACE.md#build-machines-the-supply-chain).

## Out of scope

Physical attacks, including power, electromagnetic, acoustic and thermal channels. Also extraction through ordinary correct answers and the proof system's soundness.

## Open questions

1. After failure, keep answering and count failures, or stop until reset? Stopping permits denial of service and reveals the stopping position.
2. Prevent duplicate delivery, or prove fresh computation? These are different replay properties.
3. Order globally, delaying everyone behind a silent request, or per client, allowing cross-client ordering?
4. Who can read logs that expose event counts and timing?
5. How much latency and lost availability is acceptable for less leakage?
