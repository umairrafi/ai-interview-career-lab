# Lab 7. Operate

Postings this covers: Telnyx (routing, fallbacks, cost, traces), Cohere (observable from day one), qlub (observability and LLM cost), Globant (latency and error metrics).

Code: [operate.py](../src/ledgerlab/operate.py).

Every observed gate run stores a trace: model, tool names offered on the call, input tokens, output tokens, latency, cost, route, whether the budget was exceeded, and the decision the gate made.

The router calls the primary model. If that call errors, or the cost is over the budget, it calls the fallback and records the route. A budget of zero forces the fallback, because any real call costs more than zero. An unavailable primary falls back without a budget alert.

Alerts this lab will raise:

- `cost_over_budget` when the primary call crossed the budget.
- `fallback_used` when the answer came from the fallback.
- `write_without_correlation` when a row was written with no correlation id.

Two more belong on a pager once this is in a real queue. They are named in `ALERTS` so the list is explicit. This lab does not simulate a clock for them:

- `queue_age` when a human queue item sits past the agreed age.
- `safety_bypass` when an accept happens without `decide`. The eval in lab 5 is what catches that in CI.

## Interview

**Story.** I want one trace per run: which model, which tools, how many tokens, how long it took, what it cost, and what the gate decided. If the primary call exceeds the budget or is down, the fallback answers and the trace says so. I would page on budget breaches, on fallback rate, and on any write that has no correlation id. Queue age and a safety bypass are the other two pages. I would not debug an agent from a chat transcript.

**Number.** A primary call over a zero budget is served by `fake-fallback` and raises `cost_over_budget` and `fallback_used`.

**Failure.** A written record with no correlation id raises `write_without_correlation`. That alert stays on.
