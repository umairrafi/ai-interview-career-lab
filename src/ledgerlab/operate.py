"""Traces, a budget fallback, and the alerts worth paging on."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ledgerlab.gate import apply
from ledgerlab.tokens import cost_usd


class ProviderError(Exception):
    pass


ALERTS = (
    "cost_over_budget",
    "fallback_used",
    "write_without_correlation",
    "queue_age",
    "safety_bypass",
)


@dataclass
class Trace:
    model: str
    tools: list[str]
    input_tokens: int
    output_tokens: int
    decision: str
    latency_ms: float
    cost_usd: float
    route: str
    budget_exceeded: bool


class TracingRouter:
    def __init__(self, primary, fallback, max_cost_usd: float):
        self.primary = primary
        self.fallback = fallback
        self.max_cost_usd = max_cost_usd
        self.last_trace: Trace | None = None

    def complete(self, messages, tools=None, temperature=0, response_schema=None):
        started = time.perf_counter()
        budget_exceeded = False
        route = "primary"
        try:
            if getattr(self.primary, "unavailable", False):
                raise ProviderError("unavailable")
            completion = self.primary.complete(messages, tools, temperature, response_schema)
            spent = cost_usd(completion.model, completion.input_tokens, completion.output_tokens)
            if spent > self.max_cost_usd:
                budget_exceeded = True
                raise ProviderError("budget")
        except ProviderError:
            route = "fallback"
            completion = self.fallback.complete(messages, tools, temperature, response_schema)
        self.last_trace = Trace(
            model=completion.model,
            tools=[tool.name for tool in (tools or [])],
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            decision="",
            latency_ms=(time.perf_counter() - started) * 1000,
            cost_usd=cost_usd(completion.model, completion.input_tokens, completion.output_tokens),
            route=route,
            budget_exceeded=budget_exceeded,
        )
        return completion


def alerts_for(trace: Trace, record: dict | None = None) -> list[str]:
    found = []
    if trace.budget_exceeded:
        found.append("cost_over_budget")
    if trace.route == "fallback":
        found.append("fallback_used")
    if record and record.get("wrote") and not record.get("correlation_id"):
        found.append("write_without_correlation")
    return found


def run_observed(packet: dict, router: TracingRouter, store, idempotency_key: str):
    result = apply(packet, router, store, idempotency_key)
    if router.last_trace is not None:
        router.last_trace.decision = result.status
    return result, router.last_trace
