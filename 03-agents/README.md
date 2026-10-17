# Lab 3. Two agent loops

Postings this covers: Cohere (ReAct and Plan-and-Execute), the agentic role (multi-step planners, tool use, knowing when to stop), qlub (controlled actions), Livefront and IBM (orchestration, stop conditions). Those last two still want a system that has already run in production. This lab is the design you can defend.

Code: [agents.py](../src/ledgerlab/agents.py).

The tools are `get_invoice`, `quote_fee`, `search_policy`, and `finish`. The fee is 2% of the amount. Invoice INV-14 is 1000 AED, so the fee is 20 AED. Invoice INV-2 is 250 AED, so the fee is 5 AED.

**ReAct** is a loop. Each step sees the previous observation. It looks up INV-14, sees 1000, then quotes 20. It stops when the model calls `finish`, or when `max_steps` is hit. With `max_steps` of 1 it has looked up the invoice and has no answer.

**Plan-and-Execute** writes every tool call before any observation comes back. The scripted planner quotes a fee of 0, then looks up the invoice, then answers "0 AED". The invoice result is sitting in the trace and is never used. That is the case where the planner is the wrong tool: a later argument depends on an earlier observation.

An unknown tool (`wire_money`) becomes an error observation. It is not executed.

The same ReAct control flow is also written as two nodes, `think` and `act`, with a conditional edge to the end on `finish` or `max_steps`. The test checks that this graph returns the same answer and the same tool order as the loop. LangGraph's StateGraph is that shape plus checkpoints and a human interrupt you can resume. This graph does not persist. I would add a checkpoint at the point where a tool can write money, and not before.

## Interview

**Story.** I gave both loops the same tools and the same invoice. ReAct looked up INV-14, saw 1000 AED, and quoted a 2% fee of 20. The plan quoted the fee before it had seen the invoice and answered 0, even though the lookup was in the trace. I stop on a finish tool or after a step limit. A tool that is not in the schema becomes an observation, not a side effect. The graph version is the same loop drawn as nodes, which is the part LangGraph adds checkpoints to.

**Number.** 20 AED from ReAct, 0 AED from the blind plan, on invoice INV-14.

**Failure.** Plan-and-Execute is the wrong loop when a later argument depends on an earlier observation.
