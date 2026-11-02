"""Reorder a several-client trace (observer/client.py --clients C) into the order requests were admitted.

Usage: python3 observer/by_admission.py TRACE.jsonl --clients C > ORDERED.jsonl
Client c's request in round r is the (r * C + c)-th request admitted, because the observer sends client 0
first and the rest --gap-ms apart. Each output row gets that index as "id" (in the row and its answer), so
observer/jitter_test.py and observer/estimate.py can read it like a one-client trace, with one planted
bit per admitted request. Refuses a trace that doesn't have exactly one answer per client and round.
"""
from __future__ import annotations

import argparse
import json
import sys


def by_admission(rows: list[dict], clients: int) -> list[dict]:
    if clients < 2:
        raise ValueError("clients must be at least 2")
    seen = {}
    for row in rows:
        c, r = row["client"], row["round"]
        if not (0 <= c < clients) or (c, r) in seen or row["answer"]["id"] != r:
            raise ValueError(f"unexpected row for client {c} round {r}")
        seen[(c, r)] = row
    rounds = len(seen) // clients
    if len(seen) != rounds * clients or set(seen) != {(c, r) for r in range(rounds) for c in range(clients)}:
        raise ValueError("every client must have one answer in every round")
    out = []
    for r in range(rounds):
        for c in range(clients):
            row = seen[(c, r)]
            i = r * clients + c
            out.append({**row, "id": i, "answer": {**row["answer"], "id": i}})
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace")
    ap.add_argument("--clients", type=int, required=True)
    a = ap.parse_args(argv)
    rows = [json.loads(line) for line in open(a.trace) if line.strip()]
    for row in by_admission(rows, a.clients):
        sys.stdout.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
