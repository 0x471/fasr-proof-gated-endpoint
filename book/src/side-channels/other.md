# Size, packets, queue and logs

> **In short**
> - Fixed application replies remove direct control of their size and format.
> - Fixed release removes the queue choice in the state model; logs retain other information.
> - Network packets have not yet been measured for indirect effects.

## Message size and format

**The attack.** Many formats allow several ways to write the same message. In JSON, for example, `1` and `1.0` mean the same number, and spaces and key order are free. A server could hide bits in which valid form it uses, or in how long its messages are.

**The defence.** Each message type has a fixed layout for the approved model. The server's answer can contain a bounded, variable-length proof, but verification accepts only the pinned proof length. That rejects extra bytes the proof library would otherwise accept after a valid proof.

Every reply to a user has the same size, whether it carries an answer or an error. A parsed message must re-encode to identical bytes. This checks its written form; the server's proof bytes never become the user's reply.

**Fuzzing** checks this. A fuzz test throws large numbers of random and corrupted messages at each message reader. Each must be refused, or accepted and re-encoded to identical bytes.

This is tested, not proven, and it tests the message readers, not timing. The [hardening page](../hardening.md) has the details.

## Packets on the network

Data travels in packets, each with a header: sizes, sequence numbers, flags and similar fields. A sender could hide bits in those fields.

The endpoint never forwards the server's packets. It holds two separate connections: one with each user, and its own connection out to the server. It reads the server's answer, keeps only the checked output values and writes a fresh fixed-size reply. Its own operating system then sends that reply in new packets to the user.

So the server cannot directly choose the headers or packet sizes users see. This removes direct forwarding as a route for those bits, not every possible network channel.

This is an argument, not yet a measurement. The server still decides when it answers, which could in principle change how the endpoint's operating system sends its packets. Packet captures are part of the registered timing tests, but the last runs skipped them. They are planned for the next runs on the Pi.

## Identifiers, nonces and other protocols

A nonce is a value intended for one use, often to distinguish otherwise identical requests. There is no nonce inside this prototype's proof. A proof for the same encoded input can be reused, but it must still bind to the same checked output.

The client supplies its request identifier, and the endpoint assigns a separate sequence number for the server. The endpoint restores the client identifier when replying; it does not copy a server-chosen identifier. Neither field gives the server a free payload.

The principle of ending one connection and writing a fresh reply can apply beyond TCP, the transport used here. Other protocols need their own format, metadata and timing analysis. They have not been implemented or measured in this prototype.

## The queue

The attack: the endpoint can hold only a limited number of questions at once. When the queue is full, new questions get `unavailable` immediately; `busy` is the log reason, not a wire status. A server could try to choose refusals by keeping the queue full.

The defence: an admitted question, one accepted for processing, keeps its place until release. In the fixed-release state model with halt disabled, timely and slow answers occupy places until the same targets. Thus admission depends on request times and capacity, not answer times. `endpoint/core/tests/busy_channel.rs` checks that model.

Under arrival-order release, answering early frees places, so the queue does depend on the server's speed. After a halt (see [Failures](failures.md)), refusals follow the server's failure. Delays of the endpoint's own loop under load are a separate, partly tested question.

Users cannot tell a full queue from honest heavy load. The [delivery catalogue](../attacks.md#delivery-whether-when-and-how-often-an-answer-arrives) lists each case.

## The endpoint's logs

The endpoint logs fixed result and reason words, never arbitrary server text or proof hashes. Its records also include sequence numbers, elapsed time, input hashes and halt failure counts. Input hashes can link requests, and small input sets can be guessed. Access to these records remains an open question.

Hashing a randomised proof would give the server another value to vary, so proof hashes are deliberately excluded.

The number and timing of log events still follow the server. Too many stale, duplicate or never-requested answers cause disconnection, limiting that source of log flooding. This is not a total log-size limit: new client requests and reconnects can still add records.

## Verification time

A server could send proofs that are slow to check, or that crash the checker. Each check runs in a separate process with limits and a deadline. Under fixed release, a slow check can still affect timing; a missed deadline becomes a failure. These controls do not supply a general timing bound.

## Physical channels

Power use, radio emissions, sound and heat are outside this project. The device is assumed to sit inside the data centre's own physical security. No protection against someone holding the board has been established.

Secure boot would check the software loaded at startup. A Trusted Platform Module (TPM) and a persistent counter could support protection against restoring old state. These are planned, not built, and would not by themselves address all physical channels.
