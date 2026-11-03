import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "observer"))

from shift_bound import bits_per_answer, groups, main, robust_noise, shift_interval  # noqa: E402


def planted(n, shift, sd, seed=5):
    r = random.Random(seed)
    bits = "".join(r.choice("01") for _ in range(n))
    return bits, [4000.0 + (shift if b == "1" else 0.0) + r.gauss(0, sd) for b in bits]


def test_signal_power_equal_to_noise_carries_half_a_bit():
    assert bits_per_answer(2.0, 1.0) == 0.5
    assert bits_per_answer(0.0, 1.0) == 0.0


def test_interval_covers_a_planted_shift():
    bits, ms = planted(4000, 0.2, 1.0)
    lo, hi = shift_interval(*groups(ms, bits), boot=2000)
    assert lo < 0.2 < hi and hi - lo < 0.2


def test_robust_noise_ignores_rare_late_answers():
    bits, ms = planted(1000, 0.0, 1.0)
    clean = robust_noise(*groups(ms, bits))
    ms[::50] = [m + 30.0 for m in ms[::50]]
    assert math.isclose(robust_noise(*groups(ms, bits)), clean, rel_tol=0.1)


def test_report_from_a_trace(tmp_path, capsys):
    bits, ms = planted(400, 0.0, 0.5)
    trace = tmp_path / "t.jsonl"
    trace.write_text("".join(json.dumps({"id": i, "elapsed_ms": m, "answer": {"id": i, "ok": True}}) + "\n"
                             for i, m in enumerate(ms)))
    main([str(trace), bits, "--boot", "500"])
    out = capsys.readouterr().out
    assert "n=400" in out and "bit/answer" in out
