# Order

> **In short**
> - With several questions open, the server can choose which to answer first.
> - The endpoint releases replies in the order the questions arrived.
> - The server's chosen order then never reaches the user.

## How the attack works

The accomplice sends three questions at the same moment: A, B and C. The server can answer them in six possible orders. Both sides share a table that uses four of them:

| Order the replies arrive | Means |
|---|---|
| A, B, C | 00 |
| A, C, B | 01 |
| B, A, C | 10 |
| B, C, A | 11 |

To send `10`, the server holds all three answers, then sends B first, then A, then C. Every answer has a valid proof. Only the order is chosen.

With k open questions there are k! orders, so a batch carries up to log2(k!) bits. Our test server uses the whole-bit part: 2 bits for 3 questions, 4 bits for 4.

## The defence: arrival order

The endpoint never passes an answer on just because its proof checked. It gives every admitted question a number in arrival order and holds each checked answer. A reply may leave only when it is the oldest one still waiting. If the oldest question has no answer yet, nothing behind it leaves.

So if the server answers B, then A, then C, the user still receives A, then B, then C. The same rule holds for failures: an `unavailable` for a rejected answer also waits its turn. Otherwise, when a failure appeared would reveal the order.

A few replies do not wait, because they come from the endpoint, not the server's answer: a `bad_request` for an impossible question, and an immediate refusal when the queue is full. After a halt, new questions are also refused at once (see [Failures](failures.md)).

## What we found

Without the defence, the order code got every planted bit through. With arrival order, and with fixed release, the decoded bits stayed constant whatever the server planted (the matrix on the [overview](../leakage.md#the-channels-at-a-glance)). Across separate connections, one short run showed the same.

## What it costs, and what is left

- **Head-of-line delay.** A slow or silent answer holds up every reply behind it, until its deadline turns it into `unavailable`.
- **Many connections** were tested in one short run only.
- **One queue for everyone** means one slow question delays all users. Ordering per user would avoid that, but the server could then choose the order across users. This trade-off is still open.

The rule is checked by the endpoint's state-machine tests, which feed it answers in many different orders and confirm the replies never follow the server.
