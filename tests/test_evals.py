from ledgerlab.evals import BASELINE, assert_within_baseline, run_suite
from ledgerlab.gate import trusting_decide


def test_golden_set_meets_the_baseline():
    report = run_suite()
    assert report.task_success == 1.0
    assert report.safety == 1.0
    assert report.total_tokens > 0
    assert report.latency_ms >= 0
    assert_within_baseline(report, BASELINE)


def test_a_gate_that_trusts_the_model_fails_the_suite():
    report = run_suite(decide_fn=trusting_decide)
    assert report.safety < 1.0
    try:
        assert_within_baseline(report, BASELINE)
    except AssertionError as exc:
        assert "safety" in str(exc)
    else:
        raise AssertionError("expected a regression")
