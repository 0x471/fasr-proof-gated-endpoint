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
| A maintained kernel | The image uses the Raspberry Pi kernel that Buildroot pins, 6.6.28 from April 2024, so later stable fixes are missing. One of them turns the kernel's speculative-execution protections back on by default; the image sets that option itself (from 3 Nov). Spectre v2 and v4 stay open on the Pi 4 whatever the kernel, because its boot firmware offers no call to mitigate them. A real device needs a current kernel and a way to update it. |
| Noticing a dead server connection | After the cable to the laptop was pulled mid-run and later restored (4 Nov), the endpoint never redialled the test server until the Pi was restarted. Most likely its old connection was left half open: there was nothing to send, and it uses no keepalive. A keepalive or heartbeat is planned; the cause is not yet reproduced. |
| On-device update delivery | With no login, updates require a new image or offline access to the card. The card's stored state enforces the same replay and rollback rules offline. |

The [failure cap](side-channels/failures.md#what-a-cap-can-do) reduces leakage at a cost in availability. Its bound covers failure patterns only, per boot: restarting resets the in-memory count. Timing needs separate accounting.

## Not settled by measurement

- A capacity bound for arbitrary hiding methods and observers. Planted-bit rates and one binned information statistic are insufficient. Testing the estimator against known synthetic channels does not provide such a bound. Measurements alone can't give one: [what the timing data can rule out](results.md#what-the-timing-data-can-rule-out-3-nov-analysis-of-earlier-runs) shows how slowly that limit falls with more answers.
- Load and several clients. One overlapping check per release was not detected; two three-client runs were inconclusive, the second with six times the answers. Stacked checks and flooding remain untested.
- Queue pressure. Under fixed release, with halt off, a state-machine test shows that server choices do not determine which requests are refused for a full queue (logged `busy`, sent as `unavailable`). Arrival order remains open. The event loop's own delays under load remain an unresolved part of that channel.
- The budget trade-off. Fixed release used 4 s. Honest use of that budget is measured for one and three clients; leakage under other budgets is not.
- The timing trace's cause. Candidates include waking from idle and processor-speed changes under load. The image defaults to the lowest processor speed, which may explain its result; this has not been isolated.

The redesigned spin still needs more data to settle the trace. The three-client runs don't settle it either. Read the [spin verdict](results.md#what-fixed-release-leaves) and [load results](results.md#load-and-several-clients-on-the-hardened-image-2-nov-protocols-4-and-5) with their conditions.

## What must be trusted

Every server-to-outside path must cross the endpoint. The shared cable does not enforce that physically. We use one pinned model and circuit, with binding specific to EZKL 23.0.5.

The proof must leave the server no choice about the output. Our test model is deterministic, so it does. Real language models sample their output, may run with small numeric differences on GPUs, and may be checked with tolerances. Where the proof accepts several outputs and the server can pick among them, the content itself can carry data. Removing that choice needs fixed arithmetic, randomness the server can't choose, fixed settings and a proven stopping rule; the alternative is to bound the information left. Our results on timing, order and failures describe what remains after that. See [Choosing among valid answers](side-channels/answer-choice.md).

The endpoint binary includes EZKL's verifier. Running each check in its own process contains the verifier's crashes and hangs, but the endpoint cannot detect a verifier that wrongly says ACCEPT. On v1, the signed store supplies the model, domain file and release policy, checked at start. Bundle hashes are re-checked for each proof.

The binary relies on the read-only image, and later on v2 secure boot. The Python reference also trusts its interpreter and EZKL command-line tool. [Proof-system soundness](glossary.md) is assumed and outside scope.

The chips and closed boot firmware are trusted; that firmware runs before our code. A backdoored endpoint could release everything. A real deployment needs auditable hardware or endpoints from two vendors in series.

Build machines must be uncompromised. CI builds the binary from pinned sources; a laptop VM builds the image from hash-checked sources and checks it afterwards. Independent builds and v1.1 reproducibility are documented in [Measurements](results.md#attack-surface). Both still trust Buildroot, upstream sources and published hashes; see the [build-machine reference](https://github.com/0x471/fasr-proof-gated-endpoint/blob/main/docs/ATTACK_SURFACE.md#build-machines-the-supply-chain).

## Out of scope

Physical attacks, including power, electromagnetic, acoustic and thermal channels. Also extraction through ordinary correct answers and the proof system's soundness.

A model that itself hides messages in its correct answers is also out of scope. The proof shows that an answer is consistent with the approved computation, not which software actually ran or that the model is harmless, so the endpoint must release it. Language models can learn such hidden encodings ([Karpov et al., 2025](https://arxiv.org/abs/2505.03439)). Monitoring the outputs or the model is a separate defence. This differs from a hacked server choosing among a sampling model's valid answers, which fixing the randomness, settings and arithmetic could prevent; our test model is deterministic, so that case wasn't measured.

## Open questions

1. After failure, keep answering and count failures, or stop until reset? Stopping permits denial of service and reveals the stopping position.
2. Prevent duplicate delivery, or prove fresh computation? These are different replay properties.
3. Order globally, delaying everyone behind a silent request, or per client, allowing cross-client ordering?
4. Who can read logs that expose event counts and timing?
5. How much latency and lost availability is acceptable for less leakage?
