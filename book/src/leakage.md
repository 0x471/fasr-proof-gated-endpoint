# What a hacked server can still leak

> **In short**
> - A proof fixes what an answer says, but a hacked server still controls **when** it answers, **in what order**, and **which answers fail**. Each of these can carry hidden data.
> - On the real device, with one client at a time: releasing answers in arrival order stopped the ordering code we tried, and releasing every answer at a fixed time stopped the timing code we tried, at the cost of speed. A small leftover timing trace is described below.
> - Deliberate failures leaked under every release rule we tried. A cap on failures limits that channel, at a large cost in availability; it remains the main open problem.

## Why a proof isn't enough

Think of the endpoint as a strict customs officer who checks that every parcel's contents match the paperwork. A smuggler who can't change the contents can still send a message by choosing **when** parcels arrive, **in what order**, or **which ones get rejected**. Anyone watching from outside who knows the code can read the message back.

## How we tested it

We made the server hide a known message (16 bits) in its behaviour, and had an observer outside the endpoint try to read it back with a fixed decoder. If the observer recovers all 16 bits, that channel is open. If the decoder fails, it didn't recover that message in that run; a different encoder or a smarter observer might still get something through, which is why the leftover trace was tested separately (below).

We did this on the real Raspberry Pi for three ways of signalling and three release rules, with a 4-second budget for the fixed-time rule, one client at a time.

## Results

{{#include results.md:matrix}}

What this means:

- **Order is easy to protect.** Sending answers back in the order the questions arrived removes the server's choice: the observer decoded the same bits whatever the server planted.
- **Timing costs speed to protect.** The endpoint aims to send every answer 4 seconds after its question, so a delay chosen by the server no longer shows in a simple way. But every user now waits the whole budget, even when the answer was ready much sooner (the last row above). Random delays are not a cheaper fix: the server's own delay still shifts when answers leave, an observer with enough answers can read it, and the leak per answer only shrinks as the added wait grows (a model in [Measurements](results.md#random-sleeps-instead-of-a-fixed-release-time-a-model-2-nov)).
- **A small timing trace was left.** {{#include results.md:no-spin-trace}} {{#include results.md:spin-verdict}}
- **Failures stay open.** The server can always make an answer fail by sending a bad proof, and which answers fail is itself the message: choosing one failure in every 16 answers sends 4 bits per 16 answers. {{#include results.md:failure-leak}}

## Closing the failure channel

No release rule can stop deliberate failures, because a failure looks like a real fault. What the endpoint can do is **limit how many failures it tolerates**, and count every failure, including answers the server lets miss their deadline:

- Over a window of N answers, if the observer only sees which answers failed and the endpoint allows at most F failures, the server can choose among at most C(N,0) + C(N,1) + ... + C(N,F) patterns, so it can send at most log2 of that many bits per window.
- Stopping the endpoint at the first failure in a window of N answers leaves N + 1 outcomes (no failure, or a failure at one of N positions), so at most log2(N + 1) bits per window, but only if someone decides when the endpoint restarts; and it lets the server switch the endpoint off whenever it wants.

These bounds hold only for that observation (failures only) and that policy, and per boot: the count lives in memory, so a restart starts a fresh window (K50). Timing needs its own accounting. The Rust endpoint now has such a cap, and one run on the Pi showed the trade-off: far fewer hidden bits got out, but many honest answers were refused too (numbers in [Measurements](results.md)). How the failure code scales with longer messages:

{{#include results.md:failure-scaling}}

## Questions people ask

**Why not just release every answer exactly 4 seconds after its question?** That is what the fixed rule does. The clock starts when the question arrives at the endpoint, and the answer leaves at that moment plus the budget, whatever the server did; if the server's answer isn't checked by then, the reply is "unavailable" instead, which is the failure channel. The leftover trace was not in that schedule but in how precisely the computer acts on it: waking a sleeping program and pushing a packet out takes slightly different time depending on what the processor was doing just before. When the server answered late, the endpoint had just been busy checking that proof; when it answered early, the endpoint had been idle for seconds. That is our leading explanation, not yet isolated. Waking a few milliseconds early and busy-waiting until the exact moment (the "spin") removed the difference we could see, and on the stripped image one run of the same test showed nothing.

**How can a few failures carry many bits?** The message is in which answer fails, not in how many. If one answer in each batch of 16 fails, its position (one of 16) carries 4 bits. Longer messages need proportionally more failures or longer batches; the table above shows the trade-off, and a cap limits any such code.

**Can the server hide bits in the network packets themselves (packet sizes, TCP header fields)?** Not directly. The endpoint keeps separate connections: its own connection to the server, and one with each outside client. Nothing the server sends is forwarded as packets. It reads each message, keeps only the checked output values, and writes a new reply of a fixed size. So the server never touches the outside packets' headers or sizes. What it still controls is when it answers, which answers fail, and how busy it keeps the endpoint. Under fixed release, keeping the endpoint busy doesn't decide which other users are turned away: every question holds its place until its release time whatever the server does (a test of the endpoint's state machine, K17). Whether the server's choices show up in packet-level details on the outside link hasn't been measured yet (see below).

**What was the fuzzing for?** A parser is the code that reads an incoming message (a question from a client, an answer from the server). The fuzz test throws thousands of random and corrupted messages at each one and checks that every one is either refused or, if accepted, writes back to exactly the same bytes. That makes sure malformed input can't crash or confuse the endpoint, and that a message has only one accepted form, so extra bytes or alternative encodings can't carry hidden data. It is not a timing test.

**Does this depend on EZKL or on the Raspberry Pi?** Partly. How a proof is tied to its question (the binding rules) is specific to EZKL and must be redone for any other proof system. The side-channel defences (fixed-size messages, release in arrival order or at a fixed time, the failure cap) don't depend on the proof system. What the timing defence achieves does depend on the hardware and operating system, which is why it was measured on the stock system and on the stripped image separately.

**What about physical attacks?** Out of scope: the device is assumed to sit inside the data centre's physical security. Basic measures (secure boot, a TPM, a counter that can't be rolled back) are planned as a design, not as a defence against someone with the board in hand.

## What this doesn't show

- These are the rates **one particular** hiding method achieved, not the most any method could achieve.
- One device, one network, one client at a time (the ordering test used several questions at once on one connection). With several clients, the fixed-time rule and its spin interact in ways not yet measured.
- Packet-level signals (packet sizes, network timing details) haven't been measured yet.

All numbers and their conditions are in [Measurements](results.md).
