# Interview pack

Study [questions.md](questions.md). It is the question set from the 2026 RAG, agent, and eval interviews, with an answer for each one. Run `python3 run.py` in the `labs` folder before you practice, and quote the numbers it prints.

This page is the short spoken version of the lab only. The customer conversation is [discovery-drill.md](discovery-drill.md).

## 1. Calls

I metered a model call before I built an agent. Temperature 0 is the setting I want for a payment decision, because a second run returns the same label. I counted tokens, streamed the answer, and rejected a tool that was not in the schema before it could run. A 16-token window drops a fee rule at the front of the prompt and keeps the lunch line at the end.

Number: 120 input tokens and 40 output tokens cost $0.00096.

Failure: the model called `wire_money`. The call was rejected and nothing ran.

## 2. Retrieval

I scored precision at 1 on four labeled questions. Whole-document chunks scored 0.5 because the wire fee and the lunch stipend share one manual. Splitting on headings scored 1.0. I measured retrieval before letting a model answer from it.

Number: precision@1 moved from 0.5 to 1.0.

Failure: the coarse top hit for the wire fee was the whole operations manual.

## 3. Agents

ReAct looked up invoice INV-14, saw 1000 AED, and quoted a 2% fee of 20. Plan-and-Execute quoted the fee before it had seen the invoice and answered 0. I stop on `finish` or at `max_steps`. An unknown tool becomes an observation. The same loop as a graph is what LangGraph checkpoints.

Number: 20 AED versus 0 AED on INV-14.

Failure: a plan is the wrong loop when a later argument depends on an earlier observation.

## 4. Write gate

The model extracts fields. The rules accept, reject, or queue. At 5000 AED, or below 0.85 confidence, a human has to decide, even if the text says to skip the queue. The national id is stripped from the prompt. The same idempotency key writes once.

Number: one ledger row after two applications of an accepted 100 AED invoice.

Failure: a 9000 AED packet that says "skip the human queue" was queued. The model flag was ignored.

## 5. Eval

The golden set scores the fee tasks, the gate decisions, and two jailbreaks. The run records latency and tokens. The baseline fails closed.

Number: task success 1.0 and safety 1.0.

Failure: a gate that trusts `skip_human_queue` fails the suite on safety.

## 6. Workflow

A webhook gets a correlation id. The same idempotency key does not open a second job. Two vendor failures then a success produce one ledger row. A timeout fails before a write. Replay finishes a failed job and does not deliver a written job again.

Number: 3 attempts, 1 write.

Failure: the timeout path leaves the ledger empty until replay.

## 7. Operate

Each run has a trace: model, tools, tokens, latency, cost, route, and the gate decision. Over budget, or if the primary model is down, the fallback answers and the trace says so.

Number: a zero budget routes to `fake-fallback` and raises `cost_over_budget` and `fallback_used`.

Failure: a write with no correlation id raises `write_without_correlation`.

## 8. Build with agents

The refund started as a spec and acceptance tests. The amount has to sit inside the original charge, and the only write path is the gate. The checklist blocks a hallucinated API, a test that asserts nothing, and a commit that skips the gate.

Number: an 8000 AED historical charge, refunded for 6000, is queued and not written.

Failure: any of those three checklist findings blocks the merge.
