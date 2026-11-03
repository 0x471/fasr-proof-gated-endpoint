"""What a failure-cap setting costs and what it allows: a model, not a device measurement.

For each setting (window W, failures F, cooldown C) it reports two numbers over n admitted replies:
- the bound: at most how many bits the ok/unavailable pattern can carry, whatever the server does
  (observer/cap_bound.py), per reply;
- the honest cost: the expected share of replies the cap turns into unavailable when an honest
  server's answers fail independently with probability p (a fault rate, not an attack), computed
  exactly from the cap's reference model (observer/cap_model.py).
A tighter cap lowers the bound but trips on honest faults more often; this shows by how much.
Starting from an empty cap, like the device after a boot.

    python observer/cap_curves.py --n 4096 --p 0.001 0.01
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cap_bound import bits  # noqa: E402
from cap_model import START, check, step  # noqa: E402

SETTINGS = [(16, 1, 16), (32, 1, 32), (64, 1, 32), (64, 1, 64), (64, 1, 128), (64, 2, 32), (64, 2, 64),
            (128, 1, 128)]


def honest_cost(window: int, failures: int, cooldown: int, n: int, p: float) -> float:
    """Expected share of n replies capped when each answer fails independently with probability p."""
    check(window, failures, cooldown)
    if not 0 <= p <= 1:
        raise ValueError("p must be a probability")
    states = {START: 1.0}
    capped = 0.0
    for _ in range(n):
        nxt: dict = defaultdict(float)
        for s, q in states.items():
            for failed, w in ((False, 1 - p), (True, p)):
                if w == 0:
                    continue
                s2, out = step(s, window, failures, cooldown, failed)
                if out == "capped":
                    capped += q * w
                nxt[s2] += q * w
        states = nxt
    return capped / n


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=4096)
    ap.add_argument("--p", type=float, nargs="+", default=[0.001, 0.01])
    a = ap.parse_args(argv)
    print("| W | F | C | bits per reply, at most | " + " | ".join(f"honest replies lost, p = {p}" for p in a.p) + " |")
    print("|---|---|---|---|" + "---|" * len(a.p))
    for w, f, c in SETTINGS:
        row = [f"{bits(w, f, c, a.n) / a.n:.3f}"] + [f"{100 * honest_cost(w, f, c, a.n, p):.2f} %" for p in a.p]
        print(f"| {w} | {f} | {c} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
