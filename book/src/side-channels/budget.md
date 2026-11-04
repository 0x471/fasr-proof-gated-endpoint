# From channels to a budget

> **In short**
> - Each channel's limit is per answer; multiplying by traffic gives bits per day or year.
> - The useful question is how long it would take to leak one key.
> - The policy settings trade leakage against speed and availability.

## Where each channel stands

| Channel | Status | Limit |
|---|---|---|
| Content, deterministic model | closed by the proof and binding | none left |
| Choosing among valid answers | not measured; needs pinned randomness | depends on the model and settings |
| Message size and format | closed | none left |
| Packets | server cannot set them; not measured | open question |
| Order | closed under arrival order | none left |
| Queue | closed under fixed release | none left |
| Timing | reduced by fixed release and spin | no guaranteed bound |
| Failures | limited by the cap | counted bound |
| Logs | reduced | event count and timing still follow the server |
| A model hiding messages itself | out of scope | not a gate problem |

## Turning limits into time

A per-answer limit becomes a rate once you know the traffic:

bits leaked = bits per answer x answers.

The useful question is not how many gigabytes per year, but how long one small secret takes. A key is typically a few hundred bits. Covert channels are noisy, so an attacker needs some redundancy on top.

For the failure channel the bound is counted exactly, so it can be turned into time. With no cap, a failure channel can carry up to one bit per answer, so a short key needs only a few hundred answers. With a cap:

{{#include ../results.md:key-time}}

The cap slows the leak, but it limits bits **per reply**, not in total. At a lab's traffic, even the tightest setting here passes a key's worth of bits in seconds, at the bound. So a cap alone is not a budget: a real one has to count over time, such as a limit on failures per day. The model's assumptions are on [Measurements](../results.md#from-a-per-reply-bound-to-time-a-model-3-nov).

Timing has no guaranteed limit. The [timing page](timing.md#why-measurements-cannot-prove-timing-is-safe) shows what our data can and cannot rule out.

## A policy hook

RAND's report on securing model weights recommends hardware-enforced limits on output rates at its fourth security level. It does not say how much leaks through a channel that only releases verified answers. Per-answer limits like these could fill that gap. Petrie, Muhlhauser and Drotos (2026) go further and enforce a budget of unexplained information at a gate.

## The settings a lab chooses

| Setting | Less leakage | Cost |
|---|---|---|
| Fixed release instead of arrival order | removes the queue channel and reduces timing | every reply waits the full budget |
| A longer budget | fewer honest answers miss the deadline | more delay |
| Spin before release | removes a visible timing trace | some processor time at each release |
| A tighter cap | fewer bits through failures | more answers lost during an attack |
| Stop after a failure | least leakage | the attacker gets an off switch |
| The gate supplies sampling randomness | no choice among valid answers | needs a proof system that supports it |
| Check every answer, not a sample | no unchecked answers | more proving work |

Checking only a random sample of answers can deter an attacker. It only works if the attacker cannot predict or influence which answers are checked; otherwise it simply uses the unchecked ones (Rinberg et al., 2025).

## What is still open

- What causes the remaining timing trace. On the hardened image a first test found no trace without spin, with or without a core of its own, so whether a separate core removes it is still untested where a trace exists.
- Whether several users at once open a timing channel. A larger registered test is planned.
- Whether packet details on the wire change with the server's behaviour.
- How much room real language models leave for choosing among valid answers, and how a gate would supply the randomness.
- Whether a restart should start the cap in a cooldown.
- How to count failures over time (per hour or per day) instead of per window, so the total, not only the rate, is bounded.
- Whether a lab should prefer a cap, which keeps the service up, or stopping, which leaks least.
