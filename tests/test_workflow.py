from ledgerlab.workflow import Downstream, Engine


def _body(key="wh-1"):
    return {
        "idempotency_key": key,
        "packet": {
            "client_id": "C-9",
            "amount": 100,
            "currency": "AED",
            "document_type": "invoice",
            "confidence": 0.95,
            "raw_text": "Webhook invoice 100 AED",
        },
    }


def test_duplicate_webhook_keeps_one_correlation_id():
    engine = Engine()
    first = engine.ingest(_body())
    second = engine.ingest(_body())
    assert first == second == "cor-1"


def test_two_failures_then_one_write():
    downstream = Downstream()
    downstream.fail_remaining = 2
    engine = Engine(downstream=downstream)
    correlation_id = engine.ingest(_body())
    job = engine.process(correlation_id)
    assert job["status"] == "written"
    assert job["attempts"] == 3
    assert engine.store.write_count == 1
    assert len(downstream.deliveries) == 1


def test_timeout_does_not_write_and_replay_can():
    downstream = Downstream()
    downstream.timeout = True
    engine = Engine(downstream=downstream)
    correlation_id = engine.ingest(_body("wh-2"))
    failed = engine.process(correlation_id)
    assert failed["status"] == "failed"
    assert engine.store.write_count == 0
    downstream.timeout = False
    recovered = engine.replay(correlation_id)
    assert recovered["status"] == "written"
    assert engine.store.write_count == 1
    again = engine.replay(correlation_id)
    assert again["write_id"] == recovered["write_id"]
    assert len(downstream.deliveries) == 1


def test_exhausted_retries_are_dead():
    downstream = Downstream()
    downstream.fail_remaining = 5
    engine = Engine(downstream=downstream, max_attempts=3)
    correlation_id = engine.ingest(_body("wh-3"))
    job = engine.process(correlation_id)
    assert job["status"] == "dead"
    assert engine.store.write_count == 0
