# How we test for a leak

> **In short**
> - The server hides a known message; an observer outside tries to read it back.
> - Statistical tests and honest control runs help distinguish signals from noise.
> - "Not detected" means this test missed it, not that nothing leaks.

## Plant a known message

We cannot wait for a real attacker, so we play one. A test server (`prover/server.py`) hides a known string of bits, or zeros and ones, in its behaviour. It uses valid proofs except when deliberately causing failures. Because we know the message, we can ask whether someone outside can read it back.

The test server has one mode per channel:

| Mode | How it hides the next bits |
|---|---|
| `timing_bits` | waits a little longer before answering for a 1 |
| `order_bits` | answers a batch of open questions in a chosen order |
| `fail_position` | in each block of answers, makes exactly one fail; its position is the message |
| `load_bits` | times its answers so a proof check runs right when another reply is due |

These modes change behaviour, not the checked output values.

## Read it back from outside

An observer program (`observer/client.py`) plays the accomplice. It records each reply and when the program reads it, saving a trace. These are application timestamps, not packet-capture times. A decoder, a program that translates observations back into bits, tries to recover the message.

Recovering the message shows that the tested code worked in that run. Recovering about half the random bits is consistent with chance. It does not rule out a weaker signal or a better decoder.

## Separate signal from noise

Small effects need statistics. Three tools do most of the work:

- Permutation test. We shuffle the bit labels and repeat the analysis to see how often the shuffled data looks at least as strong. The p-value estimates that fraction, with a correction for the finite number of shuffles.
- Held-out decoder. It learns a threshold and which side means 1 on half the answers, then scores the other half. We swap the halves and keep the better score. Each shuffle repeats that whole procedure, so the comparison accounts for choosing the better half.
- Honest control. We repeat the analysis on a run where the server hid nothing. A signal there warns of chance, analysis errors or environmental patterns, rather than the intended encoding.

We also report a mutual-information estimate: how many bits the binned reply time reveals about the planted bit. It describes the data; it is not a limit on what an attacker could do.

## Decide the rules before the data

For the registered timing tests, we specify the question, setup, analysis and decision rule before the run. This separates the planned test from later exploration. The protocols are in `docs/EXPERIMENT_PROTOCOL.md` and the files that follow it.

The decision rule we reuse:

- **Leak shown** if the held-out test gives p < 0.01 and the control meets the protocol's separate clean-control threshold.
- **Not detected** if the signal test meets the protocol's not-detected threshold.
- **Inconclusive** for anything in between.

The thresholds are distinct: merely missing the leak-shown threshold does not mean "not detected". The [registered spin result](../results.md#what-fixed-release-leaves) illustrates the middle case.

## Three numbers people mix up

1. Achieved rate: what one hiding method got through in one run. It demonstrates a possibility in those conditions, not a rate promised on another system.
2. Capacity: the greatest information rate the channel supports under a specified model. Usually unknown here.
3. Bound: a ceiling on the information a specified channel can carry, under stated assumptions.

"Not detected" is about the first: one decoder, one sample size, one run. It is not a statement about capacity. We have a real bound only for the [failure channel](failures.md); for [timing](timing.md) we explain why measurements alone cannot give one.

## Models and measurements

The random-sleep comparison is a simulation. The timing-shift limits use device data, then add assumptions about the noise to estimate possible information. Neither is a bound on all behaviour of the device.
