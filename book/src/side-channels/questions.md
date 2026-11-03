# Common questions

> **In short**
> - Short answers to questions readers often ask about the side channels.
> - Each answer links to the page with the full story.

## What is fuzzing for? Does it find side channels?

No. Fuzzing throws large numbers of random and corrupted messages at the endpoint's message readers. It checks that each one is refused, or accepted in exactly one written form. That protects the size and format channel and the parsers themselves. Timing, order and failures are tested with planted messages instead. See [Size, packets, queue and logs](other.md#message-size-and-format) and [How we test a channel](testing.md).

## What does "stopped" mean in the attack catalogue?

The endpoint refused the attack or made it carry nothing, and a test or a run on the Pi shows it. It does not mean the device stopped working. Attacks that still work, work in part or are untested are counted separately, each with what still gets through. See the [attack catalogue](../attacks.md).

## Why not make every reply take exactly 4 s, verification included?

That is the target, not an exact-time promise. When the endpoint accepts a question for processing, it sets a deadline using a clock unaffected by wall-clock changes. It never releases that reply before the deadline, but processing or network delays can make it late. See [Timing](timing.md#the-defence-fixed-release).

## The target is t + 4 s. Can't the accomplice see that?

Yes. The target depends on when the endpoint accepts the question, so it does not carry a secret chosen by the server. Actual arrival can still vary, and that variation is what our [timing tests](timing.md#the-leftover-trace) examine.

## What if an honest answer takes longer than 4 s?

If checking is unfinished at the deadline, the user gets `unavailable`, no earlier than t + 4 s. The budget needs to allow honest proving, transport and checking. A slower prover needs a longer budget, at the cost of more delay for every user. Deliberate misses are the [failure channel](failures.md).

## Why not add a random delay instead?

Random delays blur a timing code but do not remove it. Replies near the edges of the random window still give the bit away. See [Timing](timing.md#why-not-a-random-delay).

## Where did the small timing difference without spin come from?

{{#include ../results.md:no-spin-trace}}

The release schedule was correct. Our leading explanation is the processor's state: after seconds idle it rests more deeply and wakes a little later than after a proof check. This is not proven. Staying awake for the last moment ("spin") removed the average difference, but one registered decoder test was inconclusive, so the trace is not shown to be gone. See [Timing](timing.md#the-leftover-trace).

## How do 4 failures carry 16 bits? And how does that scale?

In each block of 16 answers the server fails exactly one. Its position, 1 to 16, is a 4-bit number. Four blocks give 16 bits. In general one failure in a block of B answers carries log2(B) bits; bigger blocks need fewer failures but more answers. See [Failures](failures.md).

## The server controls its packets. Can't it hide bits in TCP headers or packet sizes?

Not in the packets users receive. The endpoint ends the server's connection, reads the answer and writes a fresh fixed-size reply on a separate connection, sent by its own operating system. The server's header fields never leave the endpoint. Whether the server's timing changes how the endpoint's own packets are sent is not measured yet. See [Size, packets, queue and logs](other.md#packets-on-the-network).

## Is this tied to EZKL or to TCP?

The defences are not. Fixed release, arrival order, the failure cap and fresh replies do not depend on the proof system or on TCP. The parts tied to EZKL are the [binding rules](../binding-spec.md), which tie a proof to its question, and the proof's pinned length. A new proof system needs its own versions of those, and its own timing budget.

Timing behaviour does depend on the hardware and operating system, so the stock system and the stripped image were measured separately. Every rate describes the hiding methods we tested on one device and network, not the best possible attacker.

## Real language models are not deterministic. Does any of this still apply?

Yes, but it is not enough on its own. A model that samples its words lets the server choose among valid answers, a channel in the content itself. That needs the randomness pinned as well, which no system we found does while keeping the weights secret. One system instead proves how much choice was left. Our results cover what is left once that freedom is gone. See [Choosing among valid answers](answer-choice.md).

## What about power, radio or sound?

Physical channels are out of scope. The device is assumed to sit inside the data centre's physical security. See [Size, packets, queue and logs](other.md#physical-channels).

## Can measurements prove there is no timing channel?

No. A test can only say how large a channel it would have noticed. A very slow or clever code could stay below that. See [Timing](timing.md#why-measurements-cannot-prove-timing-is-safe).
