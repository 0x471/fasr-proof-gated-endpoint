import math
import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "observer"))
from sleep_vs_fixed import budget_bits, shift_bits, simulate  # noqa: E402


def test_shift_code_through_uniform_sleep_carries_delta_over_r():
    assert shift_bits(50, 1000) == 0.05
    assert shift_bits(2000, 1000) == 1.0


def test_budget_code_bounds():
    assert budget_bits(1000, 100) == (math.log2(11), math.log2(11))
    lo, hi = budget_bits(1000, 2000)
    assert lo == 0.0 and hi == math.log2(1.5)


def test_only_the_window_edges_give_the_bit_away():
    bits, ms, _ = simulate("sleep", 20000, delta=100, noise=0, r=1000, honest=0, seed=3)
    telling = sum(1 for t in ms if t < 100 or t >= 1000)
    assert abs(telling / len(ms) - 0.1) < 0.01
    assert all(b == 0 for b, t in zip(bits, ms) if t < 100)
    assert all(b == 1 for b, t in zip(bits, ms) if t >= 1000)
    assert all(100 <= t <= 1100 for b, t in zip(bits, ms) if b == 1)
    assert all(0 <= t <= 1000 for b, t in zip(bits, ms) if b == 0)


def test_fixed_release_time_does_not_depend_on_the_server():
    bits, ms, missed = simulate("fixed", 2000, delta=500, noise=20, t=4000, seed=4)
    assert set(ms) == {4000} and missed == 0 and set(bits) == {0, 1}


def test_late_answers_become_failures_not_late_releases():
    _, ms, missed = simulate("fixed", 1000, delta=4000, noise=0, t=4000, honest=800, seed=5)
    assert missed > 0 and set(ms) == {4000}
