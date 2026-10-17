"""Token estimates, context fitting, sampling, and price.

The estimator splits on words and punctuation. It is not a production
tokenizer. It is stable enough to show cost, truncation, and a budget.
"""

from __future__ import annotations

import re

TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# USD per token. Invented list prices for the two scripted models.
PRICES = {
    "fake-primary": {"input": 3e-6, "output": 15e-6},
    "fake-fallback": {"input": 1e-6, "output": 5e-6},
    "openai-compatible": {"input": 3e-6, "output": 15e-6},
}


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(TOKEN.findall(text))


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES[model]
    return input_tokens * price["input"] + output_tokens * price["output"]


def worked_cost() -> float:
    """120 input tokens and 40 output tokens on the primary model."""
    return cost_usd("fake-primary", 120, 40)


def fit_messages(messages: list[dict], max_tokens: int) -> list[dict]:
    """Keep the tail of the conversation that fits in the window.

    Older turns are dropped first. The surviving text is what the model
    can see. A fee rule at the front of a short window disappears.
    """
    if max_tokens <= 0:
        return []
    kept: list[dict] = []
    used = 0
    for message in reversed(messages):
        tokens = estimate_tokens(message.get("content", ""))
        if used + tokens > max_tokens:
            if not kept:
                kept.append({**message, "content": _tail(message.get("content", ""), max_tokens)})
            break
        kept.append(message)
        used += tokens
    kept.reverse()
    return kept


def _tail(text: str, max_tokens: int) -> str:
    parts = TOKEN.findall(text)
    tail = parts[-max_tokens:]
    return " ".join(tail)


def sample_label(options: list[str], temperature: float, seed: int) -> str:
    """Temperature 0 is repeatable. A positive temperature uses the seed."""
    if not options:
        raise ValueError("options required")
    if temperature <= 0:
        return options[0]
    return options[seed % len(options)]


def stream_text(text: str, size: int = 8):
    if size <= 0:
        raise ValueError("size must be positive")
    for start in range(0, len(text), size):
        yield text[start : start + size]


def demonstrate_context_drop(max_tokens: int = 16) -> str:
    messages = [
        {
            "role": "system",
            "content": "The domestic wire fee is 25 dirhams. " * 40,
        },
        {
            "role": "user",
            "content": "The canteen serves rice. What is for lunch?",
        },
    ]
    fitted = fit_messages(messages, max_tokens)
    return "\n".join(message["content"] for message in fitted)
