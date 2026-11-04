# Timing

> **In short**
> - The server can answer fast or slow on purpose; reply times then carry bits.
> - Each reply leaves at a fixed time after its question, so its timing no longer follows the server.
> - A tiny trace remained without "spin"; measurements cannot prove a timing channel is gone.

## How the attack works

A hacked server controls when it sends each answer. It proves the answer correctly, then simply waits before sending it when it wants to signal a 1:

| Question | Secret bit | Server | The accomplice sees |
|---|---|---|---|
| 1 | 1 | waits a second, then answers | a slow reply: 1 |
| 2 | 0 | answers at once | a fast reply: 0 |
| 3 | 1 | waits a second | slow: 1 |

The endpoint cannot simply reject slow answers. Real servers are sometimes slow for honest reasons, and "slow on purpose" looks the same. A careful attacker would also use delays of milliseconds, hidden in normal variation, and recover them with statistics.

## The defence: fixed release

Under **fixed release**, each reply leaves at its question's arrival time plus a fixed budget. Our budget is 4 s.

| Question | Arrives | Answer checked | Reply leaves |
|---|---|---|---|
| A | t | soon after | t + 4 s |
| B | t' | much later, but before t' + 4 s | t' + 4 s |
| C | t'' | not by t'' + 4 s | t'' + 4 s, as `unavailable` |

Fast or slow, the user sees the same delay. The time is public and predictable, and that is the point: it does not depend on anything the server chose. An answer that misses its time becomes a failure, which moves the signal into the [failure channel](failures.md).

The endpoint does not compute "4 s minus the verification time". When a question arrives, it records an absolute release time on a clock that never jumps, and waits for that moment.

![Admission fixes the release target; a checked answer or unavailable leaves no earlier than that target](../diagrams/fixed-release.svg)

**The cost:** every user waits the full budget, even when the answer was ready much sooner. The budget must also exceed an honest answer's time, or honest answers fail. A slower prover needs a longer budget.

## Why not a random delay?

A natural idea is to add a random wait, say between one and three seconds, to drown the server's delay in noise. We modelled this (`observer/sleep_vs_fixed.py`; a model, not a device run).

Random waits keep leaking. Suppose the server's code shifts an answer by d, and the endpoint adds a random wait between 0 and R. Most replies then reveal nothing, but those near the edges of the window reveal the bit for certain. On average the observer learns exactly d/R bits per answer. A server free to delay by more can carry more, so the random wait must grow with the server's freedom.

In the simulated runs below, every random wait still leaked, while fixed release showed nothing. The setup and the full model are in [Measurements](../results.md#random-sleeps-instead-of-a-fixed-release-time-a-model-2-nov).

{{#include ../results.md:random-sleeps}}

Fixed release removes the server's influence instead of hiding it. It is still a time delay, just not a random one.

## The leftover trace

Fixed release stopped our one-second code, but a much finer test found a trace:

{{#include ../results.md:no-spin-trace}}

The schedule was not at fault. The difference came from how quickly the computer acts on it. Our leading explanation, not yet proven:

- For a 1, the server answered late, so the endpoint had just been checking that proof. The processor was busy and awake when the release time came.
- For a 0, the server answered early, so the processor had been idle for seconds. It had dropped into a deeper rest and took a little longer to wake.

A second possibility is that the processor's speed changes with load. Either way, the server's choice changes the processor's state, and the state changes the release time slightly.

## What "spin" means

A program can wait for a moment in two ways:

- **Sleep:** ask the operating system to wake it at the target time. This is cheap, but waking takes a small, variable time.
- **Spin:** stay awake and check the clock in a loop until the target time. This is precise, but keeps a processor core fully busy.

Our endpoint sleeps until 5 ms before the release time, then spins for the last 5 ms. The processor is awake at release either way, so the server's choice should no longer change the timing.

{{#include ../results.md:spin-verdict}}

## Load and several users

A server could also try to delay releases indirectly: time its answers so that a proof check runs exactly when another reply is due, or exploit several users at once. Two registered tests looked at this on the stripped image:

{{#include ../results.md:load-and-clients}}

A longer three-user test with six times the answers is registered as protocol 6 (`docs/EXPERIMENT_PROTOCOL_3.md`) and has not run yet.

## Why measurements cannot prove timing is safe

"Not detected" is not "small". We asked how large a shift each run still allows, and what such a shift could carry under a simple noise model:

{{#include ../results.md:timing-limits}}

The limit falls only about as fast as the number of answers grows: halving it needs roughly twice the answers. A clever code could also hide in details no test looked at. So a guaranteed bound cannot come from measurement alone. Details are in [Measurements](../results.md#what-the-timing-data-can-rule-out-3-nov-analysis-of-earlier-runs).

## Two routes to a real bound

1. **Remove the server's influence by design.** Fixed release is the first step. The next is a release stage that cannot see what the checker or the server did, such as its own processor core or a separate small chip that only holds the schedule. A first test of running the release loop on its own core found nothing to remove: without spin, this image showed no trace either way.

{{#include ../results.md:own-cpu}}

2. **Charge for what is left.** Petrie, Muhlhauser and Drotos (2026) have the server commit in advance to a predicted spread of reply times, and charge each observed time against a budget of leaked bits. Their design also groups replies into fixed time windows.

The two routes combine well: the better the design removes timing freedom, the less there is to charge.
