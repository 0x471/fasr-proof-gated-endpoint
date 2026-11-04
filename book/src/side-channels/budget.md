# From channels to a budget

> **In short**
> - A leakage bound needs a stated observation window, traffic rate and set of channels.
> - A bound can limit how quickly a key leaks; it does not show a working attack.
> - The policy settings trade leakage against speed and availability.

## Where each channel stands

| Channel | Status | Limit |
|---|---|---|
| Content, deterministic toy model | output fixed under proof and binding assumptions | no alternative accepted value for the same encoded input |
| Choosing among valid answers | not measured here | depends on arithmetic, sampling and other settings |
| Application reply size and format | fixed by the endpoint | no direct choice of reply encoding |
| Packets | fresh connections prevent direct header choice | indirect effects not measured |
| Order | admitted replies written in admission order | cross-connection observations tested only briefly |
| Queue | no server choice in fixed-release state model with halt off | timing under load remains partly tested |
| Timing | simple code stopped; finer tests mixed | no bound on all timing attacks |
| Failures | optional cap | counted bound on admitted reply statuses, per boot |
| Logs | fixed words, but other fields remain | count, timing and input hashes need separate treatment |
| A model hiding messages itself | out of scope | approved content may already contain secrets |

## Turning limits into time

A key of a few hundred bits is short enough that even a slow channel matters. But "how long?" needs two answers: how many replies can carry it, and how quickly those replies can arrive.

Write B(n) for the bound in n replies. Transmitting K fresh bits requires a window whose bound reaches K. Dividing that reply count by the sustained reply rate gives a lower limit on time. It does not prove an attacker can reach the limit.

A constant bound per answer can be multiplied by the number of answers. Our cap instead counts whole status sequences from a fresh start, so use its bound for the actual window. Do not assume a short-window average remains constant after restarts. A noisy code may also need extra replies to correct errors.

For the failure channel the bound is counted exactly, so it can be turned into a reply count:

- Without a cap, choosing success or failure gives one bit per observed reply in the ideal status channel. A key of a few hundred bits then needs a few hundred replies, before any error correction.
- With a cap, the table gives the fewest admitted replies at which the counted bound reaches 256 or 2,048 bits, and how long those replies take at two traffic rates. These are necessary reply counts, not demonstrated encoding rates. Triggering cooldowns also loses successful answers.

{{#include ../results.md:key-time}}

For a client that waits for each reply before asking again, fixed release requires at least 4 s per admitted reply. Concurrent requests can change the total rate. We have no single measured time-to-key across loads, clients and channels.

The cap limits bits **per reply**, not in total. At a lab's traffic, even the tightest setting here would allow a key's worth of bits within seconds, if an attacker could reach the bound. So a cap alone is not a budget: a real one has to count over time, such as a limit on failures per hour or per day. The model's assumptions are on [Measurements](../results.md#from-a-per-reply-bound-to-time-a-model-3-nov).

Timing has no guaranteed limit. The [timing page](timing.md#why-measurements-cannot-prove-timing-is-safe) shows what our data can and cannot rule out.

## A policy hook

[RAND's *Securing AI Model Weights*](https://www.rand.org/pubs/research_reports/RRA2849-1.html) recommends hardware-enforced output-rate limits at its fourth security level. A limit on raw traffic alone does not say how much hidden information verified answers carry. Bounds on individual channels could help make that assessment.

Petrie, Muhlhauser and Drotos propose a gate that budgets unexplained information in *Verifying AI Compute by Bounding Unexplained Information Exfiltration* (2026). Their architecture is a research proposal, not a demonstrated complete budget for this endpoint.

## The settings a lab chooses

| Setting | Less leakage | Cost |
|---|---|---|
| Fixed release instead of arrival order | removes queue choice in the state model with halt off; targets do not follow server timing | every admitted reply waits the full budget |
| A longer budget | fewer honest answers miss the deadline | more delay |
| Spin before release | may reduce dependence on prior processor activity; measured verdicts remain qualified | processor time; no latest-send promise |
| A tighter cap | fewer bits through failures | more answers lost during an attack |
| Halt after a failure | only the first failure position in the simplified status model | successful service stops; refusal timing is outside that bound |
| The gate supplies sampling randomness | can fix sampling choice when all other inputs and settings are fixed | needs supporting proofs and retry controls |
| Check every released answer, not a sample | no unchecked content on the covered path | more proving work; completeness of coverage still required |

Random spot checks can detect violations probabilistically, under the protocol's assumptions. [Rinberg et al. (2025)](https://arxiv.org/abs/2511.02620) require samples the attacker cannot predict or alter. Sampling does not mean each reply was checked before release.

## What is still open

- What caused the no-spin timing trace, and whether a separate release core reduces it where a trace exists. On the hardened image a first test found no trace without spin, with or without a core of its own.
- Whether several users at once open a timing channel. Two registered tests, the second with six times the answers, were both inconclusive.
- Whether packet details on the wire change with the server's behaviour.
- How much room real language models leave for choosing among valid answers, and how a gate would supply the randomness.
- Whether a restart should start the cap in a cooldown.
- How to count failures over time (per hour or per day) instead of per window, so the total, not only the rate, is bounded.
- Whether to prefer cooldowns that resume service or a halt that stops successful replies until restart.
