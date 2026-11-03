# What a hacked server can still leak

> **In short**
> - Our toy model's proof fixes the output, under its assumptions; timing, order and failures need separate controls.
> - Each of those choices can carry hidden bits to someone outside.
> - This section explains each channel from scratch, how we tested it and what is left.

This section assumes no background in side channels. Read the pages in order, or jump to a channel from the map below. Measured numbers live on the [Measurements](results.md) page; these pages explain what they mean.

## The idea in one picture

Think of the endpoint as a customs officer checking each parcel against a list of permitted contents. Even if that check works, a smuggler can choose when parcels arrive, in what order, and which ones get rejected. An accomplice who knows the code reads those choices as a message.

That is a **side channel**: information carried by behaviour instead of content.

## Who attacks, and what they want

The attacker controls the AI server. It may be a hacker who broke in, or the model itself acting against its owners. It can decide when to answer, in what order, and whether to send a valid proof at all.

Its partner is an accomplice outside, connecting as an ordinary user and sending normal questions. Both agreed on a code in advance, so the accomplice knows how to read the server's choices.

A **small secret**, such as a decryption key or cloud credential, can matter even when a channel is slow. Our measured codes do not establish the fastest possible rate for stealing weights. [From channels to a budget](side-channels/budget.md) explains what we can say about the time needed to leak a key.

We assume the endpoint and its proof checks are trustworthy, and that the traffic being assessed passes through it. A compromised endpoint or a route around it defeats that boundary. See the [threat model](threat-model.md) and [limitations](limitations.md) for assumptions not established by the prototype.

## Why the endpoint writes a fresh reply

The endpoint holds two separate connections. Users connect to the endpoint. The endpoint connects out to the server.

When an answer arrives, the endpoint reads it, checks the proof and keeps only the checked output numbers. It then writes a brand-new reply of a fixed size on the user's connection. The server's own bytes and packets never reach the user.

So the server cannot directly choose the reply's encoding or copy its own packet headers to the user. Its behaviour can still affect timing and failures; indirect packet effects have not been measured.

## The channels at a glance

| Channel | How the server signals | Our defence | Status |
|---|---|---|---|
| [Order](side-channels/order.md) | answers open questions in a chosen order | write admitted replies in admission order | server's chosen write order removed; separate connections tested briefly |
| [Timing](side-channels/timing.md) | answers fast for a 0, slow for a 1 | fixed release targets | simple code stopped; finer tests mixed; no general bound |
| [Failures](side-channels/failures.md) | makes chosen answers fail | optional failure cap with forced cooldowns | counted bound on admitted reply statuses, per boot |
| [Choosing among valid answers](side-channels/answer-choice.md) | picks which of several accepted answers to send | fix or bound output choice | not measured: our toy relation has one output per encoded input |
| [Size, packets, queue and logs](side-channels/other.md) | varies format, packets, refusals or log events | fixed formats, fresh replies and release rules | direct choices restricted; packet effects unmeasured and logs retain information |

The core Pi experiment compared immediate forwarding, arrival-order release and fixed release, with one run per table cell. It used one client; the ordering test kept several questions open on that connection. The fixed-release budget was 4 s:

{{#include results.md:matrix}}

## How to read this section

1. [How we test for a leak](side-channels/testing.md): planted messages, decoders and what "not detected" means.
2. [Order](side-channels/order.md), [Timing](side-channels/timing.md) and [Failures](side-channels/failures.md): one channel each.
3. [Choosing among valid answers](side-channels/answer-choice.md): why real language models add a channel our test model cannot show.
4. [Size, packets, queue and logs](side-channels/other.md): other paths information could take.
5. [From channels to a budget](side-channels/budget.md): adding it up, the policy choices, and what is still open.
6. [Questions people ask](side-channels/questions.md): short answers to common reader questions.
