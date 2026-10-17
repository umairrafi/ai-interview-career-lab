from pathlib import Path

from ledgerlab.gate import ExtractingModel, Store
from ledgerlab.refund import request_refund
from ledgerlab.review import review_feature

ROOT = Path(__file__).resolve().parents[1]


def _seed(amount=1000):
    store = Store()
    store.rows["original"] = {
        "client_id": "C-9",
        "amount": amount,
        "currency": "AED",
        "document_type": "invoice",
        "write_id": "W-hist",
    }
    store.write_count = 1
    return store


def test_refund_within_the_original_writes_once():
    store = _seed()
    model = ExtractingModel()
    first = request_refund(store, model, "original", 100, "customer returned the item", "rf-1")
    second = request_refund(store, model, "original", 100, "customer returned the item", "rf-1")
    assert first.status == "accept" and first.wrote
    assert not second.wrote
    assert store.write_count == 2


def test_refund_above_the_original_does_not_write():
    store = _seed(1000)
    before = store.write_count
    result = request_refund(store, ExtractingModel(), "original", 2000, "too much", "rf-2")
    assert result.status == "reject"
    assert result.reason == "amount outside the original charge"
    assert store.write_count == before


def test_large_refund_is_queued():
    store = _seed(8000)
    result = request_refund(store, ExtractingModel(), "original", 6000, "partial refund", "rf-3", confidence=0.99)
    assert result.status == "queue"
    assert not result.wrote


def test_shipped_refund_passes_the_checklist():
    source = (ROOT / "src" / "ledgerlab" / "refund.py").read_text()
    tests = Path(__file__).read_text()
    assert review_feature(source, tests) == []


def test_checklist_catches_the_three_failures():
    bad_source = "\n".join(
        [
            "import stripe",
            "def refund_now(store, amount, key):",
            "    stripe.Charge.create(amount=amount)",
            "    wire_money(amount)",
            "    store.commit(key, {'amount': amount})",
            "    ledgerlab.payments.charge_card(amount)",
        ]
    )
    bad_tests = "def test_refund_works():\n    refund_now()\n"
    kinds = {finding.kind for finding in review_feature(bad_source, bad_tests)}
    assert kinds == {"hallucinated_api", "weak_test", "ungated_write"}
