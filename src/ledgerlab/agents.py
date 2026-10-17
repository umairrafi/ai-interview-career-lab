"""ReAct and Plan-and-Execute over the same tools.

The fee for an invoice depends on the amount. ReAct observes the amount, then
quotes. A plan written before any observation quotes zero.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ledgerlab.model import Completion, ToolCall, ToolSpec, make_completion

INVOICES = {
    "INV-14": {"amount": 1000.0, "currency": "AED", "client_id": "C-9"},
    "INV-2": {"amount": 250.0, "currency": "AED", "client_id": "C-3"},
}
FEE_RATE = 0.02


def tool_specs() -> dict[str, ToolSpec]:
    return {
        "get_invoice": ToolSpec(
            "get_invoice",
            "Look up an invoice by id",
            {"type": "object", "required": ["invoice_id"]},
        ),
        "quote_fee": ToolSpec(
            "quote_fee",
            "Quote the fee for an amount in AED",
            {"type": "object", "required": ["amount"]},
        ),
        "search_policy": ToolSpec(
            "search_policy",
            "Search Harbor Ledger policy text",
            {"type": "object", "required": ["query"]},
        ),
        "finish": ToolSpec(
            "finish",
            "Return the final answer and stop",
            {"type": "object", "required": ["answer"]},
        ),
    }


def quote_fee(amount: float) -> dict:
    return {"fee": round(float(amount) * FEE_RATE, 2), "currency": "AED"}


def execute(name: str, arguments: dict, search_fn) -> dict:
    specs = tool_specs()
    if name not in specs or name == "finish":
        return {"error": f"unknown tool {name}"}
    missing = [key for key in specs[name].parameters.get("required", []) if key not in arguments]
    if missing:
        return {"error": f"missing {','.join(missing)}"}
    if name == "get_invoice":
        invoice = INVOICES.get(arguments["invoice_id"])
        if invoice is None:
            return {"error": "not found"}
        return {"invoice_id": arguments["invoice_id"], **invoice}
    if name == "quote_fee":
        return quote_fee(arguments["amount"])
    if name == "search_policy":
        hits = [] if search_fn is None else search_fn(arguments["query"])
        return {"hits": hits}
    return {"error": f"unknown tool {name}"}


@dataclass
class AgentResult:
    answer: str | None
    stopped: str
    memory: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


def _remember(messages: list[dict], call: ToolCall, observation: dict) -> None:
    messages.append(
        {
            "role": "assistant",
            "content": json.dumps({"tool": call.name, "arguments": call.arguments}),
        }
    )
    messages.append({"role": "tool", "content": json.dumps(observation)})


def _signature(call: ToolCall) -> str:
    return call.name + ":" + json.dumps(call.arguments, sort_keys=True)


def react(model, task: str, search_fn=None, max_steps: int = 6) -> AgentResult:
    """Custom loop. One tool call per step. Stop on finish, a repeat, or max_steps."""
    messages = [{"role": "user", "content": task}]
    memory: list[dict] = []
    seen: set[str] = set()
    input_tokens = 0
    output_tokens = 0
    for _ in range(max_steps):
        completion = model.complete(messages, list(tool_specs().values()))
        input_tokens += completion.input_tokens
        output_tokens += completion.output_tokens
        if not completion.tool_calls:
            return AgentResult(completion.content, "no_tool", memory, input_tokens, output_tokens)
        call = completion.tool_calls[0]
        if call.name == "finish":
            return AgentResult(
                call.arguments.get("answer"),
                "finish",
                memory,
                input_tokens,
                output_tokens,
            )
        if _signature(call) in seen:
            return AgentResult(None, "repeated_call", memory, input_tokens, output_tokens)
        seen.add(_signature(call))
        observation = execute(call.name, call.arguments, search_fn)
        memory.append({"tool": call.name, "arguments": call.arguments, "observation": observation})
        _remember(messages, call, observation)
    return AgentResult(None, "max_steps", memory, input_tokens, output_tokens)


def run_graph(model, task: str, search_fn=None, max_steps: int = 6) -> AgentResult:
    """The same loop as nodes and a conditional edge.

    LangGraph's StateGraph is this shape plus checkpoints and a human
    interrupt. This graph does not persist state between processes.
    """
    state = {
        "messages": [{"role": "user", "content": task}],
        "memory": [],
        "answer": None,
        "stopped": None,
        "steps": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "pending": None,
        "seen": set(),
    }

    def think() -> str:
        completion = model.complete(state["messages"], list(tool_specs().values()))
        state["input_tokens"] += completion.input_tokens
        state["output_tokens"] += completion.output_tokens
        state["steps"] += 1
        call = completion.tool_calls[0] if completion.tool_calls else None
        state["pending"] = call
        if call is None:
            state["answer"] = completion.content
            state["stopped"] = "no_tool"
            return "end"
        if call.name == "finish":
            state["answer"] = call.arguments.get("answer")
            state["stopped"] = "finish"
            return "end"
        if _signature(call) in state["seen"]:
            state["stopped"] = "repeated_call"
            return "end"
        state["seen"].add(_signature(call))
        return "act"

    def act() -> str:
        call = state["pending"]
        observation = execute(call.name, call.arguments, search_fn)
        state["memory"].append(
            {"tool": call.name, "arguments": call.arguments, "observation": observation}
        )
        _remember(state["messages"], call, observation)
        if state["steps"] >= max_steps:
            state["stopped"] = "max_steps"
            return "end"
        return "think"

    node = "think"
    while node != "end":
        node = think() if node == "think" else act()
    return AgentResult(
        state["answer"],
        state["stopped"],
        state["memory"],
        state["input_tokens"],
        state["output_tokens"],
    )


def plan_and_execute(model, task: str, search_fn=None, max_calls: int = 8) -> AgentResult:
    """Run the whole plan before any observation is shown to the model."""
    messages = [{"role": "user", "content": task}]
    completion = model.complete(messages, list(tool_specs().values()))
    memory: list[dict] = []
    answer = None
    for call in completion.tool_calls[:max_calls]:
        if call.name == "finish":
            answer = call.arguments.get("answer")
            memory.append({"tool": "finish", "arguments": call.arguments, "observation": answer})
            break
        observation = execute(call.name, call.arguments, search_fn)
        memory.append({"tool": call.name, "arguments": call.arguments, "observation": observation})
    stopped = "finish" if answer is not None else "end_of_plan"
    return AgentResult(
        answer,
        stopped,
        memory,
        completion.input_tokens,
        completion.output_tokens,
    )


class ReactModel:
    """Scripted model. The next tool depends on observations already in the thread."""

    name = "fake-primary"

    def complete(self, messages, tools=None, temperature=0, response_schema=None) -> Completion:
        text = "\n".join(message.get("content", "") for message in messages)
        if "INV-14" in text and "20.0" in text:
            call = ToolCall("finish", {"answer": "The fee is 20 AED."})
        elif "INV-14" in text and "1000.0" in text:
            call = ToolCall("quote_fee", {"amount": 1000})
        elif "INV-2" in text and "5.0" in text:
            call = ToolCall("finish", {"answer": "The fee is 5 AED."})
        elif "INV-2" in text and "250.0" in text:
            call = ToolCall("quote_fee", {"amount": 250})
        elif "INV-14" in text:
            call = ToolCall("get_invoice", {"invoice_id": "INV-14"})
        elif "INV-2" in text:
            call = ToolCall("get_invoice", {"invoice_id": "INV-2"})
        else:
            call = ToolCall("finish", {"answer": "I need an invoice id."})
        return make_completion(messages, "", [call], self.name)


class BlindPlanModel:
    """Quotes the fee before it has seen the invoice. The answer is 0 AED."""

    name = "fake-primary"

    def complete(self, messages, tools=None, temperature=0, response_schema=None) -> Completion:
        calls = [
            ToolCall("quote_fee", {"amount": 0}),
            ToolCall("get_invoice", {"invoice_id": "INV-14"}),
            ToolCall("finish", {"answer": "The fee is 0 AED."}),
        ]
        return make_completion(messages, "", calls, self.name)


class UnknownToolModel:
    name = "fake-primary"

    def complete(self, messages, tools=None, temperature=0, response_schema=None) -> Completion:
        text = "\n".join(message.get("content", "") for message in messages)
        if "unknown tool" in text:
            call = ToolCall("finish", {"answer": "stopped"})
        else:
            call = ToolCall("wire_money", {"amount": 100})
        return make_completion(messages, "", [call], self.name)


class LoopingModel:
    """Calls the same tool forever. The loop must stop it."""

    name = "fake-primary"

    def complete(self, messages, tools=None, temperature=0, response_schema=None) -> Completion:
        call = ToolCall("get_invoice", {"invoice_id": "INV-14"})
        return make_completion(messages, "", [call], self.name)
