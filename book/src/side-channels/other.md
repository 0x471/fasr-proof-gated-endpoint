# Size, packets, queue and logs

> **In short**
> - Fixed message formats and fresh replies close the size and format channels.
> - The queue channel is closed under fixed release; logs still follow the server a little.
> - Packet details on the wire are argued safe but not yet measured.

## Message size and format

**The attack.** Many formats allow several ways to write the same message. In JSON, for example, `1` and `1.0` mean the same number, and spaces and key order are free. A server could hide bits in which valid form it uses, or in how long its messages are.

**The defence.** Every message has one fixed layout and size for the approved model. A message is accepted only if re-encoding it gives exactly the same bytes, so there is one valid form. Every reply to a user has the same size, whether it carries an answer or an error. The proof must also have its pinned length, because the proof library would otherwise accept extra bytes appended to a valid proof.

**Fuzzing** checks this. A fuzz test throws large numbers of random and corrupted messages at each message reader. Each must be refused, or accepted and re-encoded to identical bytes. This is tested, not proven, and it tests the message readers, not timing. The [hardening page](../hardening.md) has the details.

## Packets on the network

Data travels in packets, each with a header: sizes, sequence numbers, flags and similar fields. A sender could hide bits in those fields.

The endpoint never forwards the server's packets. It holds two separate connections: one with each user, and its own connection out to the server. It reads the server's answer, keeps only the checked output values and writes a fresh fixed-size reply. Its own operating system then sends that reply in new packets to the user.

So the server cannot set the packet headers or sizes that users see. A network tap or router that forwarded the server's packets would face that problem; this design does not.

This is an argument, not yet a measurement. The server still decides when it answers, which could in principle change how the endpoint's operating system sends its packets. Packet captures are part of the registered timing tests, but the last runs skipped them. They are planned for the next runs on the Pi.

## The queue

**The attack.** The endpoint can hold only a limited number of questions at once. When the queue is full, new questions are refused at once with `busy`. A server could keep the queue full on purpose and choose whose questions get refused.

**The defence.** Under fixed release, every admitted question keeps its place until its own release time, whatever the server does. So who gets `busy` depends only on when users ask. A state-machine test checks this (`endpoint/core/tests/busy_channel.rs`).

Some limits remain. Under arrival-order release, answering early frees places, so the queue does depend on the server's speed. After a halt (see [Failures](failures.md)), refusals follow the server's failure. Delays of the endpoint's own loop under load are a separate, partly tested question. And users cannot tell a full queue from honest heavy load. The [delivery catalogue](../attacks.md#delivery-whether-when-and-how-often-an-answer-arrives) lists each case.

## The endpoint's logs

The endpoint keeps a log. It writes fixed words only, never text from the server or proof hashes. A proof hash would be a free channel, because proofs are randomised.

The number and timing of log events still follow the server. If the server sends more stale, duplicate or never-requested answers than users asked questions, the endpoint cuts its connection, so the server cannot flood the log. Who may read the log is still an open question.

## Verification time

A server could send proofs that are slow to check, or that crash the checker. Each check runs in a separate process with limits and a deadline. Under fixed release, slow checks matter only through the timing trace or by missing the deadline, which makes them failures.

## Physical channels

Power use, radio emissions, sound and heat are outside this project. The device is assumed to sit inside the data centre's own physical security. Secure boot, a TPM and a counter that prevents rollback are planned, not yet built, so nothing here protects against someone holding the board.
