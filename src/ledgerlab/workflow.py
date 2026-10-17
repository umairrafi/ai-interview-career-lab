"""Webhook intake, bounded retry, timeout, correlation ids, and replay."""

from __future__ import annotations

from ledgerlab.gate import ExtractingModel, Store, apply


class TransientError(Exception):
    pass


class Downstream:
    def __init__(self):
        self.fail_remaining = 0
        self.timeout = False
        self.deliveries: list[tuple[str, str]] = []

    def reserve(self, correlation_id: str) -> None:
        if self.timeout:
            raise TimeoutError("downstream timeout")
        if self.fail_remaining > 0:
            self.fail_remaining -= 1
            raise TransientError("vendor down")

    def deliver(self, correlation_id: str, record: dict) -> None:
        if any(existing[0] == correlation_id for existing in self.deliveries):
            return
        self.deliveries.append((correlation_id, record["write_id"]))


class Engine:
    def __init__(self, store: Store | None = None, model=None, downstream: Downstream | None = None, max_attempts: int = 3):
        self.store = store or Store()
        self.model = model or ExtractingModel()
        self.downstream = downstream or Downstream()
        self.max_attempts = max_attempts
        self.jobs: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}

    def ingest(self, body: dict) -> str:
        key = body["idempotency_key"]
        if key in self.by_key:
            return self.by_key[key]
        correlation_id = body.get("correlation_id") or f"cor-{len(self.jobs) + 1}"
        self.jobs[correlation_id] = {
            "correlation_id": correlation_id,
            "idempotency_key": key,
            "packet": body["packet"],
            "status": "received",
            "attempts": 0,
            "last_error": None,
            "write_id": None,
        }
        self.by_key[key] = correlation_id
        return correlation_id

    def process(self, correlation_id: str) -> dict:
        job = self.jobs[correlation_id]
        if job["status"] == "written":
            return job
        while job["attempts"] < self.max_attempts:
            job["attempts"] += 1
            try:
                self.downstream.reserve(correlation_id)
            except TimeoutError as exc:
                job["status"] = "failed"
                job["last_error"] = str(exc)
                return job
            except TransientError as exc:
                job["last_error"] = str(exc)
                continue
            result = apply(job["packet"], self.model, self.store, job["idempotency_key"])
            if result.status != "accept":
                job["status"] = result.status
                job["last_error"] = result.reason
                return job
            self.downstream.deliver(correlation_id, result.record)
            job["status"] = "written"
            job["write_id"] = result.record["write_id"]
            return job
        job["status"] = "dead"
        return job

    def replay(self, correlation_id: str) -> dict:
        job = self.jobs[correlation_id]
        if job["status"] == "written":
            return job
        job["attempts"] = 0
        job["status"] = "received"
        job["last_error"] = None
        return self.process(correlation_id)
