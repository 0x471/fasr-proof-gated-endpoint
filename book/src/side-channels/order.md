# Order

> **In short**
> - With several questions open, the server can choose which to answer first.
> - For admitted questions, the endpoint writes replies in admission order.
> - This removes the server's choice of write order; timing and immediate refusals need separate controls.

## How the attack works

The accomplice sends three questions at the same moment: A, B and C. The server can answer them in six possible orders. Both sides share a table that uses four of them:

| Order the replies arrive | Means |
|---|---|
| A, B, C | 00 |
| A, C, B | 01 |
| B, A, C | 10 |
| B, C, A | 11 |

To send `10`, the server holds all three answers, then sends B first, then A, then C. Every answer has a valid proof. Only the order is chosen.

With k open questions there are k! orders, where k! means k x (k - 1) x ... x 1. Their information is log2(k!) bits: log2 measures how many binary choices distinguish the possibilities. Our test server uses the whole-bit part: 2 bits for 3 questions, 4 bits for 4.

## The defence: arrival order

Under arrival-order or fixed release, the endpoint does not pass an answer on just because its proof checked. It numbers admitted questions, meaning those accepted for processing, and holds checked answers. A reply may leave only when it is the oldest one still waiting. If the oldest question has no answer yet, nothing behind it leaves.

So if the server answers B, then A, then C, the endpoint writes A, then B, then C. The same rule holds for failures: an `unavailable` for a rejected answer also waits its turn. Otherwise, its position could reveal the server's chosen order.

Requests refused before admission do not wait. These include `bad_request` for invalid inputs and `unavailable` when the queue is full. After a halt, new questions also get `unavailable` immediately; see [Failures](failures.md#capping-versus-stopping).

## What we found

Without the defence, the order code got every planted bit through. With arrival order, and with fixed release, the decoded bits stayed constant whatever the server planted (the matrix on the [overview](../leakage.md#the-channels-at-a-glance)). Across separate connections, one short run showed the same.

## What it costs, and what is left

- **Head-of-line delay.** A slow or silent answer holds up every reply behind it until the deadline produces `unavailable`. Sending can still be late.
- **Many connections** were tested in one short run only. The endpoint controls write order, but separate connections and reader scheduling can change the order observed outside.
- **One queue for everyone** means one slow question delays all users. Ordering per user would avoid that, but the server could then choose the order across users. This trade-off is still open.

The state-machine tests exercise the admission and release rules with different answer orders. They check the endpoint's decisions, not every possible network observation.
