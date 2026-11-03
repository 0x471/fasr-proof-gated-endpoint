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

Here question 7 failed, so this block says "position 7". Every reply left at its fixed time, so timing tells the accomplice nothing. The pattern of `unavailable` replies (U) carries the message.

{{#include ../results.md:failure-leak}}

## How it scales

One failure among B answers carries log2(B) bits. Larger blocks need fewer failures but more answers per bit. For any code that uses only which answers fail:

{{#include ../results.md:failure-scaling}}

The worked scaling example is in [Measurements](../results.md#how-the-failure-code-scales).

## What a cap can do

The endpoint counts the failures the server can cause: rejected proofs, errors, missed deadlines and dropped connections. A **cap** then limits how freely those failures can be placed. With our settings:

1. At most one server-caused failure is allowed in the last 64 replies.
2. One more **trips** the cap.
3. The next 64 replies are all `unavailable`, even if the server sends perfectly valid proofs.
4. After that cooldown, counting starts fresh.

During a cooldown nothing the server does changes what users see, so it cannot encode anything there. Outside cooldowns it can fail only rarely. The window, the allowed failures and the cooldown length are all settings.

## Why that gives a real bound

The cap leaves the server far fewer possible fail-or-ok patterns, and fewer patterns mean fewer bits. A tiny example: four replies with no rule can show any of 16 patterns, which is 4 bits. If at most one of the four may fail, only 5 patterns are possible, about 2.3 bits.

In general, a window of N answers with at most F failures allows C(N,0) + C(N,1) + ... + C(N,F) patterns, where C(N,k) counts the ways to pick k failing answers. Stopping at the first failure leaves N + 1 outcomes: no failure, or where it happened.

`observer/cap_bound.py` does this counting for the real cap. It counts every reply-status sequence the cap allows, whatever the server does. The logarithm of that count is a true upper limit on the bits, for any code that uses which replies fail. It does not cover timing or logs, which are separate channels.

## Capping versus stopping

The alternative to a cap is to **stop**: answer nothing more after the first failure, until someone restarts the endpoint. This leaks least, only where the first failure happened. But it hands the attacker an off switch for the whole service.

A registered test on the Pi compared both:

{{#include ../results.md:cap-vs-halt}}

Every run matched the cap's reference model reply for reply. The honest server lost nothing under the cap. Answers were lost only while an attacker kept causing failures. Full conditions are in [Measurements](../results.md#failure-cap-versus-stopping-2-nov-protocol-3).

Which to choose is a policy decision. A cap keeps the service running and raises an alarm. Stopping blocks everything until a person steps in. That depends on whether losing service or losing a secret is worse.

## Restarts

The cap's count lives in memory, so any restart starts a fresh window: the bound holds per boot. The server cannot trigger a restart today, because nothing restarts a stopped endpoint and no crash path is known. One option is to start every boot in a cooldown. That keeps restarts from giving the server a free window, at the cost of losing the first replies after each reboot. It is not built yet.
