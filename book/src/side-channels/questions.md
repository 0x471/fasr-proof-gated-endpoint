# Common questions

> **In short**
> - Short answers to questions readers often ask about the side channels.
> - Each answer links to the page with the full story.

## What is fuzzing for? Does it find side channels?

Our fuzz tests throw random and corrupted messages at the endpoint's message readers. Each must be refused or re-encode to identical bytes. This tests parsing and alternative encodings that could carry hidden data, but does not prove the format has no flaws.

These tests do not measure timing, order or failures. We test those with planted messages instead. See [Size, packets, queue and logs](other.md#message-size-and-format) and [How we test a channel](testing.md).

## What does "stopped" mean in the attack catalogue?

The cited test or Pi run rejected that attack or stopped its planted message under the stated conditions. It does not mean every variation is impossible, or that the device stopped working. Other rows describe attacks that remain, intentional allowances and cases outside scope. Read each row's evidence and caveats in the [attack catalogue](../attacks.md).

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

Our leading explanation is that the processor's state after idle time differs from its state just after checking a proof. This is not proven. Spin means staying awake and checking the clock in a loop near release time.

With spin, no average shift was detected, but one registered decoder test was inconclusive. Another run on the stripped image was not detected; neither establishes absence of a channel. The runs do not isolate spin as the cause of the difference. See [Timing](timing.md#the-leftover-trace).

## How do 4 failures carry 16 bits? And how does that scale?

In each block of 16 answers the server fails exactly one. The 16 possible positions encode 4 bits, and four blocks give 16 bits. In general, B positions give log2(B) bits of choice; our code uses power-of-two block sizes. Bigger blocks need fewer failures but more answers; see [Failures](failures.md#how-it-scales).

## The server controls its packets. Can't it hide bits in TCP headers or packet sizes?

It cannot copy those fields into the user's packets directly. The endpoint reads the server's answer and writes a fresh fixed-size reply on a separate connection. Its own operating system sends the packets. Whether server behaviour changes those packets indirectly is not measured yet; see [Packets](other.md#packets-on-the-network).

## What about nonces and protocols other than TCP?

A nonce is a value intended for one use, often to distinguish requests. This proof has no nonce; reusing a proof for the same encoded input is allowed. Client identifiers and the endpoint's sequence numbers are not server-chosen payloads, and proof bytes are discarded.

Ending connections and constructing fresh replies could apply to other protocols, but their metadata and timing need separate checks. Only TCP is implemented and measured here. See [Identifiers, nonces and other protocols](other.md#identifiers-nonces-and-other-protocols).

## Is this tied to EZKL or to TCP?

The design ideas apply more widely, but the implementation and measurements are specific. EZKL is the proof system used here; TCP carries the messages. Fixed release, arrival order and failure counting can be reused as ideas, not as already-tested implementations for another stack.

The [binding rules](../binding-spec.md) tie an EZKL proof to its question and checked output. The proof's pinned length is also specific. Another proof system needs its own binding and length checks, plus a suitable deadline.

Timing behaviour does depend on the hardware and operating system, so the stock system and the stripped image were measured separately. Every rate describes the hiding methods we tested on one device and network, not the best possible attacker.

## Real language models are not deterministic. Does any of this still apply?

Yes, but only after addressing content choice. Sampling chooses among possible tokens, or text pieces. If the proof accepts several choices that the server can control, content may carry a message. Fixing randomness, arithmetic and other settings can remove that choice; another approach bounds residual information.

Our deterministic toy model does not test either extension to real language models. See [Choosing among valid answers](answer-choice.md), including the limits of the systems compared there.

## What do timing and ordering attacks look like in practice?

For timing, our server proves an answer and adds a wait for a 1-bit, but no extra wait for a 0-bit. "Faster" means omitting that delay, not making the proof calculation faster. For order, it holds several proved answers and sends them in a chosen permutation. See the worked [timing](timing.md#how-the-attack-works) and [order](order.md#how-the-attack-works) examples.

## How long would it take to leak a key?

There is no single measured time-to-key for this device. The failure-status bound limits how many bits fit in a given reply count, per boot. Converting that to time needs a traffic rate, and does not show the bound is achievable. Timing and other excluded observations prevent a complete leakage bound; see [From channels to a budget](budget.md#turning-limits-into-time).

## What about power, radio or sound?

Physical channels are out of scope. The device is assumed to sit inside the data centre's physical security. See [Size, packets, queue and logs](other.md#physical-channels).

## Can measurements prove there is no timing channel?

No. A finite test can miss a weak signal or an encoding it was not designed to detect. Estimating what it could rule out requires a statistical model. See [Timing](timing.md#why-measurements-cannot-prove-timing-is-safe).
