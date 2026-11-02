"""Check a failure-position run reply by reply against the cap model, and count what got through.

Usage: python3 observer/cap_check.py TRACE.jsonl BITS [--batch 16] [--cap W F C | --halt N]
The server failed one chosen answer per batch (prover/server.py --mode fail_position); this replays
that intent through observer/cap_model.py (or a halt after N failures) and compares the predicted
ok/unavailable sequence with the observed one. Prints the match, the decoded bits, bit errors and
how many answers were ok. A sequential client is assumed: replies leave in request order.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cap_model import START, check, step  # noqa: E402
from client import decode_failure_position  # noqa: E402


def intended(bits: str, batch: int, n: int) -> list[bool]:
    k = batch.bit_length() - 1
    out = []
    for i in range(n):
        block, pos = divmod(i, batch)
        chunk = bits[block * k:(block + 1) * k].ljust(k, "0")
        out.append(pos == int(chunk, 2))
    return out


def predict(failed: list[bool], cap: tuple[int, int, int] | None, halt: int | None) -> list[bool]:
    """Whether each reply is ok, given which answers the server failed."""
    ok, state, count = [], START, 0
    for f in failed:
        if halt is not None:
            # A halt answers everything unavailable from the failure that reaches N onwards.
            count += f
            ok.append(not f and count < halt)
        elif cap is not None:
            state, verdict = step(state, *cap, f)
            ok.append(verdict == "pass" and not f)
        else:
            ok.append(not f)
    return ok


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace")
    ap.add_argument("bits")
    ap.add_argument("--batch", type=int, default=16)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--cap", type=int, nargs=3, metavar=("W", "F", "C"))
    g.add_argument("--halt", type=int)
    a = ap.parse_args(argv)
    if a.cap:
        check(*a.cap)
    rows = [json.loads(line) for line in open(a.trace) if line.strip()]
    observed = [r["answer"]["ok"] for r in rows]
    expected = predict(intended(a.bits, a.batch, len(rows)), tuple(a.cap) if a.cap else None, a.halt)
    mismatch = [i for i, (o, e) in enumerate(zip(observed, expected)) if o != e]
    got = decode_failure_position(rows, a.batch)
    errs = sum(x != y for x, y in zip(got, a.bits)) + abs(len(got) - len(a.bits))
    print(json.dumps({"n": len(rows), "model_match": not mismatch, "first_mismatches": mismatch[:5],
                      "decoded": got, "bit_errors": errs, "bits": len(a.bits), "ok": sum(observed)}))


if __name__ == "__main__":
    main()
