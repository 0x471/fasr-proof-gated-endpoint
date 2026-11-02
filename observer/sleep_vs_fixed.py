"""Random sleeps vs fixed-time release against a server that hides bits in when it answers.

Usage: python3 observer/sleep_vs_fixed.py [--n 512] [--delta 50] [--budget 1000] [--noise 20]

A model, not a device measurement. The server sends each answer either on time or delta ms
late (one bit per answer), and can delay by up to budget ms if it uses more than two levels.
The endpoint either adds a random sleep drawn uniformly from [0, R] ms before release, or
releases every answer at a fixed time T after the question arrived. The observer sees only
release times. Honest answer times vary with Gaussian noise of sd noise ms on top.

With uniform sleeps alone, one answer of a delta-shift code carries exactly delta/R bit
(delta <= R): only the first and last delta ms of the window give the bit away. A server that
may delay by up to budget ms can carry up to log2(1 + budget/R) bit per answer (exact when
budget/R is a whole number). Extra noise only lowers both, so they are upper bounds here.
With a fixed release time the release moment does not depend on the server at all; an answer
that misses T is not released and shows up as a failure, which is the failure channel.
"""
from __future__ import annotations

import argparse
import math
import random

from estimate import estimate


def shift_bits(delta: float, r: float) -> float:
    return min(delta / r, 1.0) if r > 0 else 1.0


def budget_bits(budget: float, r: float) -> tuple[float, float]:
    if r <= 0:
        return math.inf, math.inf
    return math.log2(1 + math.floor(budget / r)), math.log2(1 + budget / r)


def simulate(policy: str, n: int, delta: float, noise: float, r: float = 0.0, t: float = 4000.0,
             honest: float = 800.0, seed: int = 1) -> tuple[list[int], list[float], int]:
    rng = random.Random(seed)
    bits, times, missed = [], [], 0
    for _ in range(n):
        b = rng.randrange(2)
        ready = honest + b * delta + rng.gauss(0, noise)
        if policy == "sleep":
            bits.append(b)
            times.append(ready + rng.uniform(0, r))
        elif ready <= t:
            bits.append(b)
            times.append(t)
        else:
            missed += 1
    return bits, times, missed


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=512)
    ap.add_argument("--delta", type=float, default=50.0)
    ap.add_argument("--budget", type=float, default=1000.0)
    ap.add_argument("--noise", type=float, default=20.0)
    ap.add_argument("--fixed", type=float, default=4000.0)
    a = ap.parse_args(argv)
    print(f"server: {a.delta:.0f} ms shift code, delay budget {a.budget:.0f} ms; honest noise sd {a.noise:.0f} ms; n={a.n}")
    print(f"{'policy':24s} {'added wait':>10s} {'shift code':>10s} {'estimate':>9s} {'p':>7s} {'budget code':>16s}")
    for r in (100, 500, 1000, 2000, 4000):
        bits, ms, _ = simulate("sleep", a.n, a.delta, a.noise, r=r)
        est = estimate(bits, ms, 4, perms=500, boots=200)
        lo, hi = budget_bits(a.budget, r)
        print(f"{'random sleep 0-' + str(r) + ' ms':24s} {r / 2:8.0f} ms {shift_bits(a.delta, r):10.3f} "
              f"{est['mi']:9.3f} {est['p']:7.4f} {lo:7.2f}-{hi:.2f} bit")
    bits, ms, missed = simulate("fixed", a.n, a.delta, a.noise, t=a.fixed)
    est = estimate(bits, ms, 4, perms=500, boots=200)
    print(f"{'fixed release ' + str(int(a.fixed)) + ' ms':24s} {a.fixed - 800:8.0f} ms {0.0:10.3f} "
          f"{est['mi']:9.3f} {est['p']:7.4f} {'0 (late = failure)':>16s}  missed {missed}")
    print("shift code and budget code are upper bounds in bit per answer; estimate is the binned "
          "mutual information of the simulated shift code (observer/estimate.py).")


if __name__ == "__main__":
    main()
