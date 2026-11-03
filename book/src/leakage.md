# What a hacked server can still leak

> **In short**
> - A proof fixes what an answer says, but not when it leaves, in what order, or whether it fails.
> - Each of those choices can carry hidden bits to someone outside.
> - This section explains each channel from scratch, how we tested it and what is left.

This section assumes no background in side channels. Read the pages in order, or jump to a channel from the map below. Measured numbers live on the [Measurements](results.md) page; these pages explain what they mean.

## The idea in one picture

Think of the endpoint as a customs officer. Every parcel is checked against its paperwork, so nobody can change what is inside. But a smuggler can still choose **when** parcels arrive, **in what order**, and **which ones get rejected**. An accomplice who knows the code reads those choices as a message.

That is a **side channel**: information carried by behaviour instead of content.

## Who attacks, and what they want

The attacker controls the AI server. It may be a hacker who broke in, or the model itself acting against its owners. It can decide when to answer, in what order, and whether to send a valid proof at all.

Its partner is an **accomplice outside**. The accomplice is just an ordinary user who sends normal questions. Both agreed on a code in advance, so the accomplice knows how to read the server's choices.

Stealing whole model weights this way would be slow, because these channels carry little per answer. The real danger is a **small secret**, such as a key that decrypts the weights or a cloud credential. Such secrets are short, so even a slow channel can matter. [From channels to a budget](side-channels/budget.md) works through how long that takes.

## Why the server cannot touch what users receive

The endpoint holds two separate connections. Users connect to the endpoint. The endpoint connects out to the server.

When an answer arrives, the endpoint reads it, checks the proof and keeps only the checked output numbers. It then writes a brand-new reply of a fixed size on the user's connection. The server's own bytes and packets never reach the user.

So the server cannot set reply sizes or packet details directly. What it still controls is behaviour: timing, order and failures.

## The channels at a glance

| Channel | How the server signals | Our defence | Status |
|---|---|---|---|
| [Order](side-channels/order.md) | answers open questions in a chosen order | release replies in the order questions arrived | closed |
| [Timing](side-channels/timing.md) | answers fast for a 0, slow for a 1 | release every reply at a fixed time after its question | reduced; no guaranteed bound |
| [Failures](side-channels/failures.md) | makes chosen answers fail | cap how many failures it may cause | limited, with a counted bound |
| [Choosing among valid answers](side-channels/answer-choice.md) | picks which of several correct answers to send | the proof must leave no choice | not measured: our test model has one answer per question |
| [Size, packets, queue and logs](side-channels/other.md) | varies message format, packets, refusals or log events | fixed formats, fresh replies, fixed release, fixed log words | mostly closed; packets not measured |

The core experiment, run on the Pi, shows the first three side by side:

{{#include results.md:matrix}}

## How to read this section

1. [How we test for a leak](side-channels/testing.md): planted messages, decoders and what "not detected" means.
2. [Order](side-channels/order.md), [Timing](side-channels/timing.md) and [Failures](side-channels/failures.md): one channel each.
3. [Choosing among valid answers](side-channels/answer-choice.md): why real language models add a channel our test model cannot show.
4. [Size, packets, queue and logs](side-channels/other.md): the smaller channels.
5. [From channels to a budget](side-channels/budget.md): adding it up, the policy choices, and what is still open.
6. [Questions people ask](side-channels/questions.md): short answers to questions reviewers raised.
