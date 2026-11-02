import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "observer"))
from cap_check import intended, predict  # noqa: E402


def test_one_failure_per_batch_at_the_coded_position():
    failed = intended("0111", 4, 8)
    # 2 bits per batch of 4: "01" fails position 1, "11" position 3, as prover/server.py encodes them.
    assert failed == [False, True, False, False, False, False, False, True]


def test_no_policy_passes_every_answer_the_server_did_not_fail():
    failed = [False, True, False, True]
    assert predict(failed, None, None) == [True, False, True, False]


def test_halt_stops_everything_from_the_nth_failure():
    failed = [False, True, False, True, False]
    assert predict(failed, None, 2) == [True, False, True, False, False]
    assert predict(failed, None, 1) == [True, False, False, False, False]


def test_cap_cooldown_refuses_the_next_replies():
    failed = [True, False, True, False, False, False]
    assert predict(failed, (4, 1, 2), None) == [False, True, False, False, False, True]
