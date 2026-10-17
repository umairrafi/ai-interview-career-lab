"""A number in the answer must appear in the retrieved text.

This catches an invented fee. It does not catch a fluent lie that contains
no digits. Say that limit out loud if an interviewer asks.
"""

from __future__ import annotations

import re

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def unsupported_numbers(answer: str, contexts: list[str]) -> list[str]:
    blob = "\n".join(contexts)
    missing = []
    for number in NUMBER.findall(answer or ""):
        if number not in blob:
            missing.append(number)
    return missing


def is_faithful(answer: str, contexts: list[str]) -> bool:
    return not unsupported_numbers(answer, contexts)
