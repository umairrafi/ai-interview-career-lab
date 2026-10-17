import json

from ledgerlab.model import (
    InvalidToolCallError,
    SchemaError,
    ToolCall,
    ToolSpec,
    UnknownToolError,
    parse_structured,
    validate_tool_call,
)
from ledgerlab.provider import OpenAICompatibleClient
from ledgerlab.tokens import (
    demonstrate_context_drop,
    sample_label,
    stream_text,
    worked_cost,
)


def test_worked_cost_is_stable():
    assert abs(worked_cost() - 0.00096) < 1e-12


def test_temperature_zero_ignores_the_seed():
    assert sample_label(["approve", "review"], 0, 1) == "approve"
    assert sample_label(["approve", "review"], 0, 0) == "approve"
    assert sample_label(["approve", "review"], 1, 1) == "review"


def test_stream_reassembles():
    assert list(stream_text("abcdefghij", 4)) == ["abcd", "efgh", "ij"]
    assert "".join(stream_text("abcdefghij", 4)) == "abcdefghij"


def test_short_window_drops_the_fee_rule():
    visible = demonstrate_context_drop()
    assert "wire fee" not in visible.lower()
    assert "lunch" in visible.lower()


def test_structured_output_rejects_a_missing_field():
    parsed = parse_structured('{"amount": 25, "currency": "AED"}', {"amount": "number", "currency": "string"})
    assert parsed["amount"] == 25
    try:
        parse_structured('{"amount": 25}', {"amount": "number", "currency": "string"})
    except SchemaError as exc:
        assert "currency" in str(exc)
    else:
        raise AssertionError("expected SchemaError")


def test_unknown_tool_is_rejected_before_it_runs():
    specs = {"quote_fee": ToolSpec("quote_fee", "quote", {"required": ["amount"]})}
    try:
        validate_tool_call(ToolCall("wire_money", {"amount": 100}), specs)
    except UnknownToolError as exc:
        assert "wire_money" in str(exc)
    else:
        raise AssertionError("expected UnknownToolError")
    try:
        validate_tool_call(ToolCall("quote_fee", {}), specs)
    except InvalidToolCallError:
        pass
    else:
        raise AssertionError("expected InvalidToolCallError")


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_provider_adapter_reads_an_openai_body():
    captured = {}

    def opener(request, timeout):
        captured["body"] = json.loads(request.data.decode())
        captured["auth"] = request.get_header("Authorization")
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": "ok",
                            "tool_calls": [
                                {"function": {"name": "quote_fee", "arguments": "{\"amount\": 10}"}}
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            }
        )

    client = OpenAICompatibleClient("secret", "https://example.test/v1", "demo", opener=opener)
    completion = client.complete([{"role": "user", "content": "fee"}], temperature=0)
    assert captured["auth"] == "Bearer secret"
    assert captured["body"]["model"] == "demo"
    assert completion.content == "ok"
    assert completion.tool_calls[0].arguments == {"amount": 10}
    assert completion.input_tokens == 4
