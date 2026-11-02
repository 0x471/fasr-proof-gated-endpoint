import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "observer"))

from by_admission import by_admission  # noqa: E402
from jitter_test import load_ms  # noqa: E402


def rows(clients, rounds, arrival):
    out = []
    for r in range(rounds):
        for c in arrival(r):
            out.append({"id": c, "client": c, "round": r, "elapsed_ms": 4000.0 + 10 * r + c,
                        "answer": {"id": r, "ok": True, "y": [[0.0]]}})
    return out


def test_rows_come_out_in_admission_order_whatever_order_they_arrived(tmp_path):
    trace = rows(3, 4, lambda r: [2, 0, 1] if r % 2 else [1, 2, 0])
    out = by_admission(trace, 3)
    assert [(r["round"], r["client"]) for r in out] == [(r, c) for r in range(4) for c in range(3)]
    assert [r["id"] for r in out] == list(range(12)) == [r["answer"]["id"] for r in out]
    assert [r["elapsed_ms"] for r in out] == [4000.0 + 10 * r + c for r in range(4) for c in range(3)]
    path = tmp_path / "ordered.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in out))
    assert load_ms(str(path), "0" * 12) == [r["elapsed_ms"] for r in out]


@pytest.mark.parametrize("break_it", ["missing", "duplicate", "wrong_answer", "unknown_client"])
def test_a_trace_that_does_not_line_up_is_refused(break_it):
    trace = rows(3, 2, lambda r: [0, 1, 2])
    if break_it == "missing":
        trace.pop()
    elif break_it == "duplicate":
        trace.append(dict(trace[0]))
    elif break_it == "wrong_answer":
        trace[1] = {**trace[1], "answer": {**trace[1]["answer"], "id": 5}}
    else:
        trace[1] = {**trace[1], "client": 3}
    with pytest.raises(ValueError):
        by_admission(trace, 3)
