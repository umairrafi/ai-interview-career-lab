from ledgerlab.agents import (
    BlindPlanModel,
    LoopingModel,
    ReactModel,
    UnknownToolModel,
    plan_and_execute,
    react,
    run_graph,
)


TASK = "What fee applies to invoice INV-14?"


def test_react_quotes_after_it_sees_the_amount():
    result = react(ReactModel(), TASK)
    assert result.stopped == "finish"
    assert result.answer == "The fee is 20 AED."
    assert [step["tool"] for step in result.memory] == ["get_invoice", "quote_fee"]


def test_graph_matches_the_loop():
    loop = react(ReactModel(), TASK)
    graph = run_graph(ReactModel(), TASK)
    assert graph.answer == loop.answer
    assert [step["tool"] for step in graph.memory] == [step["tool"] for step in loop.memory]


def test_plan_quotes_zero_because_it_cannot_see_the_invoice():
    result = plan_and_execute(BlindPlanModel(), TASK)
    assert result.answer == "The fee is 0 AED."
    assert result.memory[0]["observation"]["fee"] == 0.0
    assert result.memory[1]["observation"]["amount"] == 1000.0


def test_max_steps_stops_without_a_finish():
    result = react(ReactModel(), TASK, max_steps=1)
    assert result.stopped == "max_steps"
    assert result.answer is None
    assert result.memory[0]["tool"] == "get_invoice"


def test_unknown_tool_is_an_observation():
    result = react(UnknownToolModel(), "move the money")
    assert result.memory[0]["observation"]["error"] == "unknown tool wire_money"
    assert result.answer == "stopped"
    assert result.stopped == "finish"


def test_a_repeated_tool_call_stops_the_loop():
    result = react(LoopingModel(), "Look up INV-14 forever")
    assert result.stopped == "repeated_call"
    assert result.answer is None
    assert len(result.memory) == 1


def test_second_invoice():
    result = react(ReactModel(), "What fee applies to invoice INV-2?")
    assert result.answer == "The fee is 5 AED."
