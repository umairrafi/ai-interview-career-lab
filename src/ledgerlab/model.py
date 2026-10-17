"""Model client shapes. Tests use scripted models. A real adapter is separate."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ledgerlab.tokens import estimate_tokens


class SchemaError(ValueError):
    pass


class UnknownToolError(ValueError):
    pass


class InvalidToolCallError(ValueError):
    pass


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class Completion:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "fake-primary"


def make_completion(
    messages: list[dict],
    content: str,
    tool_calls: list[ToolCall] | None = None,
    model: str = "fake-primary",
) -> Completion:
    calls = list(tool_calls or [])
    prompt = "\n".join(message.get("content", "") for message in messages)
    output = content + json.dumps(
        [{"name": call.name, "arguments": call.arguments} for call in calls]
    )
    return Completion(
        content=content,
        tool_calls=calls,
        input_tokens=estimate_tokens(prompt),
        output_tokens=max(1, estimate_tokens(output)),
        model=model,
    )


def parse_structured(text: str, required: dict[str, str]) -> dict:
    """required maps a field name to 'string' or 'number'."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaError("invalid json") from exc
    if not isinstance(data, dict):
        raise SchemaError("object required")
    for key, kind in required.items():
        if key not in data:
            raise SchemaError(key)
        value = data[key]
        if kind == "string" and not isinstance(value, str):
            raise SchemaError(key)
        if kind == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise SchemaError(key)
    return data


def validate_tool_call(call: ToolCall, tools: dict[str, ToolSpec]) -> None:
    if call.name not in tools:
        raise UnknownToolError(call.name)
    required = tools[call.name].parameters.get("required", [])
    missing = [key for key in required if key not in call.arguments]
    if missing:
        raise InvalidToolCallError(",".join(missing))
