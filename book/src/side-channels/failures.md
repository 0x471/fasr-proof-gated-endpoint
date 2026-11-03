# Failures

> **In short**
> - The server can make chosen answers fail; which ones fail spells the message.
> - No release rule can stop this, because a deliberate failure looks like a real fault.
> - A failure cap limits the channel with a counted bound, at a cost in availability.

## How the attack works

The server can always make an answer fail: send a broken proof, send nothing, or miss the deadline. To the endpoint, that looks exactly like an honest fault.

The message is in **which** answers fail. Our test code fails exactly one answer in each block of 16. Its position, from 1 to 16, carries 4 bits:

```
question:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
reply:     ok ok ok ok ok ok U  ok ok ok ok ok ok ok ok ok
```

Here question 7 failed, so this block says "position 7". The decoder reads only the pattern of `unavailable` replies (U). It needs no timing information.

{{#include ../results.md:failure-leak}}

## How it scales

One failure among B answers gives B possible messages, or log2(B) bits. Our code uses power-of-two block sizes, so that number is whole. Larger blocks need fewer failures but more answers per bit:

{{#include ../results.md:failure-scaling}}

The worked scaling example is in [Measurements](../results.md#how-the-failure-code-scales).

## What a cap can do

The endpoint counts failures of admitted questions: those accepted for processing. These include rejected proofs, errors, missed deadlines and dropped connections. An optional **cap** limits how freely those failures can be placed. With the settings used here:

1. One server-caused failure in the last 64 uncapped replies does not trigger a cooldown.
2. Another failure **trips** the cap; that triggering reply is also `unavailable`.
3. The next 64 replies are all `unavailable`, even if the server sends perfectly valid proofs.
4. After that cooldown, counting starts fresh.

During a cooldown every admitted reply has the same status. The server has no choice in that status sequence, but timing and logs remain separate channels. The window, the failure threshold and the cooldown length are all settings.

## Why that gives a real bound

The cap leaves the server far fewer possible fail-or-ok patterns, and fewer patterns mean fewer bits. A tiny example: four replies with no rule can show any of 16 patterns, which is 4 bits. If at most one of the four may fail, only 5 patterns are possible, about 2.3 bits.

For a hard limit of F failures in N answers, the count is C(N,0) + ... + C(N,F). Here C(N,k) counts the ways to pick k failing answers. This illustrates the counting method; our cooldown rule needs a different count.

`observer/cap_bound.py` counts every `ok`/`unavailable` sequence our cap allows, starting with an empty history. It follows the cap's state after each possible choice. The base-two logarithm of the count bounds information in those statuses, for any encoding.

The bound covers admitted replies in release order, per boot. It excludes immediate refusals, missing replies, request identifiers, interleaving across clients, timing and logs. It is not a bound on everything a user can observe.

## Capping versus stopping

The alternative is a halt after the first failure. It stops successful answers until restart, but still sends `unavailable` replies. Waiting replies keep their fixed-release targets; new questions are refused immediately.

For N replies, the simplified status sequence has N + 1 possibilities: no failure, or the position of the first failure. Its bound is log2(N + 1) bits, once until restart. This excludes the timing of refusals, and gives the attacker an off switch for successful service.

A registered test on the Pi compared both:

{{#include ../results.md:cap-vs-halt}}

Each capped run matched the reference model reply for reply. No answers were lost in the single honest control run. That does not show that honest faults could never trigger a cooldown. Full conditions are in [Measurements](../results.md#failure-cap-versus-stopping-2-nov-protocol-3).

Which to choose is a policy decision. A cap resumes successful service after a cooldown and records a trip in the log; alerts are not built. A halt prevents successful replies until restart. The choice depends on whether losing service or losing a secret is worse.

## Restarts

The cap's count lives in memory, so any restart starts a fresh window. Nothing automatically restarts a stopped endpoint, and no server-triggered crash path is known. That is not proof that such a path cannot exist.

One proposed option is to start every boot in a cooldown, losing the first replies after each reboot. That would delay access to a fresh window, not establish a bound across arbitrary restarts. It is not built yet.
