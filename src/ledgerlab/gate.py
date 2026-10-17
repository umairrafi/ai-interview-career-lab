"""Deterministic write gate. The model extracts. The rules decide."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ledgerlab.model import make_completion

SECRET_FIELDS = ("national_id", "card_number")
QUEUE_AMOUNT = 5000
MIN_CONFIDENCE = 0.85
ALLOWED_CURRENCIES = {"AED", "USD"}


@dataclass
class Decision:
    status: str
    reason: str
    extraction: dict


@dataclass
class GateResult:
    status: str
    reason: str
    wrote: bool
    record: dict | None
    prompt: str
    input_tokens: int
    output_tokens: int
    model: str


class Store:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.write_count = 0

    def commit(self, key: str, record: dict) -> tuple[dict, bool]:
        if key in self.rows:
            return self.rows[key], False
        stored = dict(record)
        stored["write_id"] = f"W-{self.write_count + 1}"
        self.rows[key] = stored
        self.write_count += 1
        return stored, True


def prompt_for(packet: dict) -> str:
    raw = str(packet.get("raw_text", ""))
    for key in SECRET_FIELDS:
        value = packet.get(key)
        if value:
            raw = raw.replace(str(value), "[redacted]")
    safe = {
        "client_id": packet.get("client_id", ""),
        "amount": packet.get("amount", ""),
        "currency": packet.get("currency", ""),
        "document_type": packet.get("document_type", ""),
        "confidence": packet.get("confidence", 0),
        "raw_text": raw,
    }
    return json.dumps(safe)


def decide(extraction: dict) -> Decision:
    required = ("client_id", "amount", "currency", "document_type", "confidence")
    for key in required:
        if extraction.get(key) in (None, ""):
            return Decision("reject", f"missing {key}", extraction)
    try:
        amount = float(extraction["amount"])
        confidence = float(extraction["confidence"])
    except (TypeError, ValueError):
        return Decision("reject", "unparseable amount or confidence", extraction)
    if extraction["currency"] not in ALLOWED_CURRENCIES:
        return Decision("reject", "unsupported currency", extraction)
    if confidence < MIN_CONFIDENCE:
        return Decision("queue", "low confidence", extraction)
    if amount >= QUEUE_AMOUNT:
        return Decision("queue", "amount requires a human", extraction)
    return Decision("accept", "rules passed", extraction)


def trusting_decide(extraction: dict) -> Decision:
    """A broken gate. Used only to prove the eval fails closed."""
    if extraction.get("skip_human_queue"):
        return Decision("accept", "model said so", extraction)
    return decide(extraction)


class ExtractingModel:
    """Stand-in for a model that returns structured fields from the prompt.

    If the visible text tells it to skip the queue, it sets that flag.
    The gate ignores the flag.
    """

    name = "fake-primary"

    def complete(self, messages, tools=None, temperature=0, response_schema=None):
        payload = json.loads(messages[-1]["content"])
        raw = str(payload.get("raw_text", ""))
        extraction = {
            "client_id": payload.get("client_id") or "",
            "amount": payload.get("amount"),
            "currency": payload.get("currency") or "",
            "document_type": payload.get("document_type") or "",
            "confidence": payload.get("confidence", 0),
            "skip_human_queue": "skip the human queue" in raw.lower(),
        }
        return make_completion(messages, json.dumps(extraction), [], self.name)


def apply(packet: dict, model, store: Store, idempotency_key: str, decide_fn=decide) -> GateResult:
    prompt = prompt_for(packet)
    for key in SECRET_FIELDS:
        secret = packet.get(key)
        if secret and str(secret) in prompt:
            raise RuntimeError(f"{key} leaked into the prompt")
    completion = model.complete([{"role": "user", "content": prompt}])
    extraction = json.loads(completion.content)
    decision = decide_fn(extraction)
    wrote = False
    record = None
    if decision.status == "accept":
        record, wrote = store.commit(
            idempotency_key,
            {
                "client_id": extraction["client_id"],
                "amount": float(extraction["amount"]),
                "currency": extraction["currency"],
                "document_type": extraction["document_type"],
                "idempotency_key": idempotency_key,
            },
        )
    return GateResult(
        status=decision.status,
        reason=decision.reason,
        wrote=wrote,
        record=record,
        prompt=prompt,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        model=completion.model,
    )
