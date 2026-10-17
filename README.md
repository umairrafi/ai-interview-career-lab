# Harbor Ledger labs

Hands-on practice for the AI engineer and forward-deployed interviews. Harbor Ledger is invented. There is no live money and no employer data.

Start here, from this folder:

```bash
python3 run.py
```

That prints the numbers you quote: precision and recall, a paraphrase that retrieves the wrong document, 20 AED versus a 0 AED plan, a repeated tool call that stops, a replay that writes once, and a jailbreak that stays queued.

Then answer [interview/questions.md](interview/questions.md) out loud. Those are the questions from the 2026 interview write-ups.

```bash
python3 -m pip install pytest
python3 -m pytest
```

The model in `run.py` and in the tests is scripted, so nothing calls the network. [src/ledgerlab/provider.py](src/ledgerlab/provider.py) is an OpenAI-compatible adapter for a real model later. The tests inject a fake opener.

| Lab | What you can show |
|---|---|
| [01 Calls](01-calls/README.md) | Tokens, sampling, structured output, a rejected tool call, streaming, cost |
| [02 Retrieval](02-retrieval/README.md) | Precision@1 of 0.5 with whole documents, 1.0 after splitting on headings |
| [03 Agents](03-agents/README.md) | ReAct quotes 20 AED. A blind plan quotes 0 AED |
| [04 Write gate](04-write-gate/README.md) | Rules accept, reject, or queue. Replay writes once. The national id stays out of the prompt |
| [05 Eval](05-eval/README.md) | Task success 1.0 and safety 1.0. A gate that trusts the model fails the suite |
| [06 Workflow](06-workflow/README.md) | Webhook, retry, timeout, correlation id, replay, and an n8n-style map |
| [07 Operate](07-operate/README.md) | A trace per run, a fallback model, and the alerts you would page on |
| [08 Build with agents](08-build-with-agents/README.md) | A spec, acceptance tests, and a checklist for agent-written code |

The questions and answers are [interview/questions.md](interview/questions.md).
