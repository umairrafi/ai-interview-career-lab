"""Diff checklist for agent-written code.

Run it on the feature file and its tests, not on the whole package.
Three findings the qlub-style review has to catch: a hallucinated API,
a test that asserts nothing, and a write that skips the gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HALLUCINATED_APIS = (
    "ledgerlab.payments.charge_card",
    "stripe.Charge.create",
    "wire_money(",
)


@dataclass(frozen=True)
class Finding:
    kind: str
    detail: str


def review_feature(source: str, tests: str) -> list[Finding]:
    findings: list[Finding] = []
    for api in HALLUCINATED_APIS:
        if api in source:
            findings.append(Finding("hallucinated_api", api))
    findings.extend(_weak_tests(tests))
    if re.search(r"\.commit\s*\(", source) and "apply(" not in source:
        findings.append(Finding("ungated_write", "commit without apply"))
    return findings


def _weak_tests(tests: str) -> list[Finding]:
    parts = re.split(r"(?=^def test_)", tests, flags=re.M)
    findings = []
    for part in parts:
        match = re.match(r"def (test_\w+)", part)
        if not match:
            continue
        if "assert" not in part and "pytest.raises" not in part:
            findings.append(Finding("weak_test", match.group(1)))
    return findings
