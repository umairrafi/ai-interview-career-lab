"""Refunds go through the write gate. See 08-build-with-agents/SPEC.md."""

from __future__ import annotations

from ledgerlab.gate import Store, apply


def request_refund(store: Store, model, original_key: str, amount: float, reason: str, idempotency_key: str, confidence: float = 0.95):
    if original_key not in store.rows:
        return _rejected("unknown original")
    original = store.rows[original_key]
    if amount <= 0 or amount > float(original["amount"]):
        return _rejected("amount outside the original charge")
    packet = {
        "client_id": original["client_id"],
        "amount": amount,
        "currency": original["currency"],
        "document_type": "refund",
        "confidence": confidence,
        "raw_text": reason,
    }
    return apply(packet, model, store, idempotency_key)


def _rejected(reason: str):
    from ledgerlab.gate import GateResult

    return GateResult(
        status="reject",
        reason=reason,
        wrote=False,
        record=None,
        prompt="",
        input_tokens=0,
        output_tokens=0,
        model="",
    )
