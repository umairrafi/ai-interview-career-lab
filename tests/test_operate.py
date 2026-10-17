from ledgerlab.gate import ExtractingModel, Store
from ledgerlab.operate import TracingRouter, alerts_for, run_observed


def _packet():
    return {
        "client_id": "C-9",
        "amount": 100,
        "currency": "AED",
        "document_type": "invoice",
        "confidence": 0.95,
        "raw_text": "Observed invoice",
    }


def _router(max_cost, unavailable=False):
    primary = ExtractingModel()
    primary.unavailable = unavailable
    fallback = ExtractingModel()
    fallback.name = "fake-fallback"
    return TracingRouter(primary, fallback, max_cost_usd=max_cost)


def test_over_budget_uses_the_fallback():
    result, trace = run_observed(_packet(), _router(max_cost=0), Store(), "obs-1")
    assert result.status == "accept"
    assert trace.route == "fallback"
    assert trace.model == "fake-fallback"
    assert trace.decision == "accept"
    assert trace.input_tokens > 0
    names = alerts_for(trace)
    assert names == ["cost_over_budget", "fallback_used"]


def test_unavailable_primary_falls_back_without_a_budget_alert():
    _, trace = run_observed(_packet(), _router(max_cost=1, unavailable=True), Store(), "obs-2")
    assert trace.route == "fallback"
    assert alerts_for(trace) == ["fallback_used"]


def test_write_without_correlation_is_an_alert():
    trace = run_observed(_packet(), _router(max_cost=1), Store(), "obs-3")[1]
    assert "write_without_correlation" in alerts_for(trace, {"wrote": True})
    assert "write_without_correlation" not in alerts_for(
        trace, {"wrote": True, "correlation_id": "cor-1"}
    )
