import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "observer"))

from cap_curves import honest_cost  # noqa: E402
from cap_model import START, step  # noqa: E402


def simulate(window, failures, cooldown, n, p, rng):
    s, capped = START, 0
    for _ in range(n):
        s, out = step(s, window, failures, cooldown, rng.random() < p)
        capped += out == "capped"
    return capped / n


def test_no_faults_cost_nothing():
    assert honest_cost(16, 1, 16, 200, 0.0) == 0.0


def test_every_answer_failing_matches_the_cap_by_hand():
    # Window 4, one failure allowed, cooldown 4: fail, trip, then 4 capped, and again: 4 of every 6.
    assert honest_cost(4, 1, 4, 600, 1.0) == pytest.approx(4 / 6, abs=1e-9)


def test_exact_cost_agrees_with_simulation():
    rng = random.Random(7)
    runs = [simulate(8, 1, 8, 400, 0.05, rng) for _ in range(3000)]
    assert honest_cost(8, 1, 8, 400, 0.05) == pytest.approx(sum(runs) / len(runs), abs=0.003)


def test_bad_probability_is_refused():
    with pytest.raises(ValueError):
        honest_cost(8, 1, 8, 10, 1.5)
