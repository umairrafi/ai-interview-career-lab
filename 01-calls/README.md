# Lab 1. Calls

Postings this covers: Cohere (LLM stack), qlub (LLM APIs, tool calling), Globant UAE (structured output, token budgets), Fuse (production LLM calls), the agentic role (function calling, streaming, context windows).

Code: [tokens.py](../src/ledgerlab/tokens.py), [model.py](../src/ledgerlab/model.py), [provider.py](../src/ledgerlab/provider.py). Tests: [test_calls.py](../tests/test_calls.py).

What is here:

- A token estimate, used for cost and for the context window.
- Temperature 0 always returns the first label. A positive temperature uses the seed, so two seeds can disagree.
- Structured output rejects a missing field instead of guessing it.
- A tool call is checked against the schema. `wire_money` is not in the schema, so it never runs.
- Streaming is reassembled from chunks.
- Price for the scripted primary model is $0.000003 per input token and $0.000015 per output token.

## Interview

**Story.** I metered a model call before I built an agent. Temperature 0 is the setting I want for a payment decision, because a second run returns the same label. I counted tokens, streamed the answer, and rejected a tool that was not in the schema before it could run. I also put a fee rule at the front of the prompt and a lunch question at the end. With a 16-token window the fee rule is gone and the lunch line is what the model can see. That is the failure mode of a long context, not a smarter prompt.

**Number.** 120 input tokens and 40 output tokens on the primary model cost $0.00096.

**Failure.** The model called `wire_money`. Validation raised an unknown-tool error. Nothing was executed.
