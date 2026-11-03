"""How much a mean-shift timing code could carry, given what a run showed.

Usage: python3 observer/shift_bound.py TRACE.jsonl BITS [--per-hour 900] [--boot 20000]

Under fixed release the server can only nudge when an answer leaves. This takes a run where the
server planted BITS (1 = it tried to delay) and asks: how large could the true shift between bit-1
and bit-0 answers be, and how many bits per answer would a shift that large carry?

- The shift's 95% interval comes from a bootstrap that resamples each label group separately.
- The noise is the robust spread (1.4826 x median absolute deviation from each group's median),
  which ignores the rare very late answers; a smaller noise figure gives a larger bound.
- Bits per answer: 0.5 * log2(1 + (shift / 2)^2 / noise^2), the capacity of a channel with Gaussian
  noise and that much signal power, which no binary code can exceed under that model.

This bounds the encoder used in that run, read as a shift of the mean, under a Gaussian noise model.
It is not a bound on every code: another encoder may shift times further; noise that isn't Gaussian
can let a code carry more than the formula says (for a given spread, Gaussian noise is the worst
case for the sender); and no finite run can rule out a code that hides information in fine detail of
the time distribution. A guaranteed bound has to come from the design, not from measurement.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics

from jitter_test import load_ms


def groups(ms: list[float], labels: str) -> tuple[list[float], list[float]]:
    one = [m for m, b in zip(ms, labels) if b == "1"]
    zero = [m for m, b in zip(ms, labels) if b == "0"]
    if len(one) < 2 or len(zero) < 2:
        raise SystemExit("need at least two answers for each bit")
    return one, zero


def shift_interval(one: list[float], zero: list[float], boot: int, seed: int = 1) -> tuple[float, float]:
    r = random.Random(seed)
    diffs = sorted(
        statistics.fmean(r.choices(one, k=len(one))) - statistics.fmean(r.choices(zero, k=len(zero)))
        for _ in range(boot)
    )
    return diffs[int(0.025 * (boot - 1))], diffs[int(0.975 * (boot - 1))]


def robust_noise(one: list[float], zero: list[float]) -> float:
    dev = [abs(m - statistics.median(g)) for g in (one, zero) for m in g]
    return 1.4826 * statistics.median(dev)


def bits_per_answer(shift: float, noise: float) -> float:
    if noise <= 0:
        raise SystemExit("noise must be positive")
    return 0.5 * math.log2(1 + (shift / 2) ** 2 / noise**2)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("trace")
    ap.add_argument("bits")
    ap.add_argument("--per-hour", type=float, default=900.0, help="answers per hour (one client at 4 s: 900)")
    ap.add_argument("--boot", type=int, default=20000)
    a = ap.parse_args(argv)
    one, zero = groups(load_ms(a.trace, a.bits), a.bits)
    lo, hi = shift_interval(one, zero, a.boot)
    noise = robust_noise(one, zero)
    largest = max(abs(lo), abs(hi))
    per_answer = bits_per_answer(largest, noise)
    print(f"n={len(one) + len(zero)}  shift(1-0)={statistics.fmean(one) - statistics.fmean(zero):+.4f} ms  "
          f"95% interval [{lo:+.4f}, {hi:+.4f}] ms  robust noise={noise:.4f} ms")
    print(f"a shift of {largest:.4f} ms carries at most {per_answer:.5f} bit/answer under the Gaussian model, "
          f"{per_answer * a.per_hour:.2f} bit/hour at {a.per_hour:g} answers/hour")


if __name__ == "__main__":
    main()
