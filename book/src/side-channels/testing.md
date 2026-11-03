# How we test for a leak

> **In short**
> - The server hides a known message; an observer outside tries to read it back.
> - Statistical tests and honest control runs separate real signals from noise.
> - "Not detected" means this test missed it, not that nothing leaks.

## Plant a known message

We cannot wait for a real attacker, so we play one. A test server (`prover/server.py`) proves every answer correctly, but hides a known random bit string in its behaviour. Because we know the message, the question becomes simple: can someone outside read it back?

The test server has one mode per channel:

| Mode | How it hides the next bits |
|---|---|
| `timing_bits` | waits a little longer before answering for a 1 |
| `order_bits` | answers a batch of open questions in a chosen order |
| `fail_position` | in each block of answers, makes exactly one fail; its position is the message |
| `load_bits` | times its answers so a proof check runs right when another reply is due |

Every answer still carries a valid proof, except the deliberate failures. The leak is only in behaviour.

## Read it back from outside

An observer program (`observer/client.py`) plays the accomplice. It sends ordinary questions, records each reply and the exact time it arrived, and saves the result as a trace. A fixed decoder then tries to recover the planted bits.

If the decoder recovers every bit, the channel is clearly open. If it recovers about half, it is guessing: that is what chance gives for random bits.

## Separate signal from noise

Small effects need statistics. Three tools do most of the work:

- **Permutation test.** We compare reply times for the 1-bits and the 0-bits. Then we shuffle the labels thousands of times and see how often chance alone gives a difference as large. That fraction is the p-value.
- **Held-out decoder.** A decoder learns a threshold on one half of the answers and is scored on the other half. This stops it from fitting noise.
- **Honest control.** We repeat the analysis on a run where the server hid nothing. Anything "found" there is noise or a bug.

We also report a mutual-information estimate: how many bits the binned reply time reveals about the planted bit. It describes the data; it is not a limit on what an attacker could do.

## Decide the rules before the data

For the important timing tests, we write the protocol before running anything: the question, the setup, the analysis and how each outcome will be read. That stops us from choosing an analysis after seeing the result. The protocols are in `docs/EXPERIMENT_PROTOCOL.md` and the files that follow it.

The decision rule we reuse:

- **Leak shown** if the held-out test gives p < 0.01 and the honest control does not.
- **Not detected** if the held-out test is clearly not significant.
- **Inconclusive** for anything in between.

## Three numbers people mix up

1. **Achieved rate:** what one hiding method got through in one run. An attacker can do at least this well.
2. **Capacity:** the most any hiding method could get through. Usually unknown.
3. **Bound:** a proven ceiling on that capacity, under stated assumptions.

"Not detected" is about the first: one decoder, one sample size, one run. It is not a statement about capacity. We have a real bound only for the [failure channel](failures.md); for [timing](timing.md) we explain why measurements alone cannot give one.

## Models and measurements

Two results come from models rather than the device: the comparison of random sleeps with fixed release, and the limit on timing shifts. Both pages say so where they use them.
