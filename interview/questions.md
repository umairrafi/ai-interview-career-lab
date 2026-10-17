# Questions these interviews actually ask

Sources, read on 17 October 2026:

- [34 RAG, agent, and eval questions](https://masterprompting.net/blog/ai-engineer-interview-questions-rag-agents-evals), MasterPrompting, 8 October 2026
- [AI engineer interview questions 2026](https://techscreen.app/articles/ai-engineer-llm-interview-questions-2026), TechScreen
- [Applied-AI interview loop](https://www.techinterview.org/post/3233476824/ai-engineer-interview-rag-agents-evals/), techinterview.org
- [Production AI engineer interview kit](https://productionaiengineer.com/resources/interview-kit)

Run this first, from this repository, and keep the output in front of you:

```bash
python3 run.py
```

Answer out loud. The model in that session is scripted, so say that in the first minute. The measurements it prints are the ones to quote. Do not claim Harbor Ledger served customers.

## RAG

**1. Walk me through a RAG pipeline and where it fails.**

Ingest the documents, split them, turn each chunk into something you can search, and store it. At question time, search, optionally rerank, put the best chunks in the prompt, and generate. Each stage fails differently: a bad split, a search that shares no words with the question, a right chunk that the model ignores, or a source that is stale. I check retrieval first. If the right chunk is not in the top results, changing the prompt cannot fix the answer.

In the lab, whole documents score precision@1 of 0.5 and recall@3 of 0.5. Splitting on headings scores 1.0 and 1.0. Recall did not rise with a bigger k on the whole documents, because the labeled paragraph was never a chunk.

**2. A user says the answer is wrong. What do you do?**

I pull the query, the chunks and their scores, the prompt, and the answer. Then I classify it. If the right chunk is missing, it is retrieval. If the right chunk is there and the answer ignores it, it is generation. If the source itself is wrong, it is data. I add that query to the eval set before I change anything, or the same bug comes back.

**3. How do you choose chunk size?**

There is no universal size. Small chunks are precise and lose surrounding context. Large chunks keep context and dilute the match. I split on structure, headings and paragraphs, and I decide by measuring recall on my own questions. Tables and code I keep whole. In the lab the only change was heading splits, and precision@1 moved from 0.5 to 1.0 on the same four questions.

**4. What is the difference between dense, sparse, and hybrid search?**

Sparse search, BM25 or the term weights in this lab, needs the same words. It is strong on ids, error codes, and names. Dense search embeds the meaning, so a paraphrase can hit. Hybrid fuses the two lists. Reciprocal rank fusion is the usual way: score each item by the sum of `1 / (60 + rank)`. I would not mix the raw scores, because they are on different scales.

The lab shows the sparse miss. The query "what do we charge to send money abroad" returns `kyc-policy#vendor-data`. The wire-fee paragraph says "international wire fee" and shares almost none of those words. A synonym expansion, which stands in for a dense model so this runs with no API key, returns `operations-manual#wire-fees`. I do not call that synonym list an embedding model.

**5. Why add a reranker, and what does it cost?**

The first search is fast and approximate. A reranker reads the query and each candidate together, which is more accurate and slower, so I rerank only the top 20 to 100 and pass the best few to the model. I keep it only if recall or answer quality on the eval set rises by more than the latency I add. This lab does not include a reranker. I would say that.

**6. How do you evaluate retrieval separately from the answer?**

Labeled questions. Recall@k asks whether the right chunk is in the top k. Precision@k asks what fraction of the top k is relevant. Mean reciprocal rank asks how high the first relevant hit sits. Then score the answer on its own, for correctness and for faithfulness to the chunks. If you only score the final answer, you cannot tell whether a change helped the search or the model.

**7. What is contextual retrieval?**

A chunk that says "the fee is 25" does not say the fee for what. Contextual retrieval asks a model, at index time, to prepend a line about where the chunk sits, then embeds that. Anthropic reported their top-20 retrieval failures falling from 5.7% to 1.9% after contextual embeddings, contextual BM25, and a reranker, on their data, not mine. The cost is one model call per chunk every time you re-index.

**8. The model ignores the retrieved context. Why?**

The relevant part is buried in the middle of a long prompt. Liu and others showed in 2023 that models use the start and the end of the context more reliably than the middle. Or the prompt does not require the answer to come from the chunks. Or the model's prior disagrees with the document. I would put the best chunk first, send fewer chunks, and require a citation. I check by removing the chunk and seeing whether the answer changes.

**9. How do you handle "the answer is not in the documents"?**

Search always returns k chunks. I keep a set of questions whose correct answer is "not found", I allow the prompt to abstain, and I tune any score cutoff on both answerable and unanswerable questions. A cutoff alone is fragile. It moves when the corpus or the embedding model changes.

**10. How do you keep an index fresh?**

Hash the document. Re-embed only what changed. Delete old chunks by document id. Store the embedding model name with the index. If I switch embedding models, I re-embed everything. Vectors from two models are not comparable.

**11. When would you not use RAG?**

If the corpus fits in the context window and rarely changes, a long prompt can be simpler. If the task is a format or a tone, prompting is enough. If the question is a sum over rows, I query the database. Long context does not remove cost, latency, or the middle-of-context problem.

## Agents and tools

**12. What is the difference between a workflow and an agent?**

Anthropic's definition: a workflow is model calls on a path my code chooses. An agent is the model choosing the next tool. I start with the workflow. I add an agent only when the next step depends on what the last step returned, and I can show that on an eval. The fee in this lab is 2 percent of a known amount. That is a function. The model is only there to choose the tool.

**13. Describe the agent loop and the stop conditions.**

The model sees the goal and the tool schemas, asks for one tool or gives an answer, my code runs the tool, and the result goes back into the context. I stop on a finish tool, on a step limit, on a repeated identical call, and on a token or cost budget. "Until the model says it is done" is not a stop condition. In the lab, ReAct on INV-14 calls `get_invoice`, then `quote_fee`, then finishes with 20 AED. A model that calls `get_invoice` forever stops as `repeated_call` after one execution.

**14. How do you design a tool?**

A name that says what it does, a description that includes the edge case, a schema with required fields, and an error the model can use. `get_invoice` with a missing id returns `missing invoice_id`. It does not throw. `wire_money` is not in the schema, so the loop records `unknown tool wire_money` and does not run it.

**15. How many tools is too many?**

When tool-choice accuracy on the eval set drops, or two tools with similar descriptions get confused. I then narrow the list, or route to a smaller set. There is no magic count.

**16. A tool returns garbage, or the call is not safe to retry. What then?**

Return a structured error. Retry only calls that are safe to repeat, with a cap. A charge, a refund, or an email is not safe to repeat. Those take an idempotency key and, above a limit, a person. The lab gate writes once for key `pay-1`. The second call returns the same row and `wrote` is false.

**17. How do you handle prompt injection when the agent reads a document?**

The document is data, not instructions. A better system prompt is not the boundary. The boundary is which tools exist and which of them can write. In the lab, text that says "skip the human queue" on a 9000 AED invoice is queued. The model sets a skip flag. `decide` never reads that flag.

**18. What is MCP, and how is it different from a tool call?**

A tool call is the model asking my process to run a function I declared in that request. MCP is a protocol so a separate server can publish tools and files to any client that speaks it. They are different layers. Connecting many MCP servers puts more tool definitions in the prompt and trusts servers I do not control. I have not shipped an MCP server. I would say that.

**19. How does an agent remember a long task?**

The context window is the working memory. Past that, I summarise old turns or write the facts I must not lose, amounts and decisions, to a store and read them back. A summary drops exact numbers. I pin those instead of hoping the summary keeps them. The lab shows the cheap version of this failure: a 16-token window drops the fee rule and leaves "The canteen serves rice. What is for lunch?"

**20. When is more than one agent worth it?**

When the work splits into parallel parts, or the parts need different permissions. It costs more tokens and it is harder to debug. I would want a measured gain over one agent first. The smallest version is one orchestrator that hands out a bounded task and takes back a short result.

**21. What would you never let an unattended agent do?**

Move money, delete data, or send a message to a customer, without a rule and, above a threshold, a person. Also a sandbox, a step cap, a budget, and a trace of every tool call. In the lab the threshold is 5000 AED or confidence below 0.85.

## Evaluation

**22. How do you start evaluating when you have no data?**

Write 20 to 50 realistic inputs and a pass or fail for each. Run them on every change. Add every production failure to the set. My set is small on purpose: two fee questions, three gate cases, two jailbreaks. Task success and safety are both 1.0, and the run records tokens. The last run used 1052 tokens.

**23. When is an LLM-as-judge acceptable?**

When the quality is not a string I can check, and I have a narrow rubric. I compare the judge to a human on a labeled sample before I trust it. Judges prefer longer answers and the first side of a pair. I do not have a judge in this lab. The faithfulness check here is deterministic: every number in the answer must appear in the retrieved text. "25" passes against "25 dirhams". "99" fails. That check does not catch a fluent lie with no digits.

**24. Which metrics for a RAG system?**

Retrieval: recall@k and mean reciprocal rank. Generation: correctness against a reference, faithfulness to the chunks, and the rate of correct abstention. I trust an automated faithfulness score least until a person has reviewed a sample of its disagreements.

**25. How do you evaluate an agent, not a single call?**

Score the end state, not only the final sentence. Also score the tools used, the step count, forbidden actions, cost, and latency. Run the same task more than once. The τ-bench paper measured pass^k, success on all k trials, and reported pass^8 under 25% for strong function-calling agents in its retail domain. One lucky success is not reliability. My lab runs once per task because the model is scripted. On a real model I would repeat the trial.

**26. How do you catch a regression when you change a prompt or a model?**

Pin the eval set. Run before and after. Compare each category, not only the average. A flat average can hide a jailbreak regression under a better fee answer. I proved the suite can fail: `trusting_decide` accepts when the model says to skip the queue, safety drops below 1.0, and the baseline check raises on safety.

**27. How do you evaluate in production?**

Sample traces. Watch retries, abandons, cost, and latency. Put failures back into the golden set. Thumbs-up data is sparse and biased to the extremes, so I do not steer on it alone.

## Cost, latency, and reliability

**28. The bill doubled. What do you check?**

Per-request input and output tokens, by feature and by model, before I look at the invoice. Usual causes: more chunks in the prompt, extra agent steps, retries, a model change, or a new caller. Then shorten the context, cache the stable prefix, or send easy cases to a cheaper model. The lab prices are invented so the arithmetic is visible: 120 input tokens at $0.000003 and 40 output tokens at $0.000015 is $0.00096.

**29. How does prompt caching help, and when does it not?**

The provider reuses a long identical prefix, so the system prompt and the stable documents get cheaper on the next call. Anything that changes must come after that prefix. A timestamp at the top of the system prompt breaks the cache.

**30. How do you reduce latency?**

Stream the answer, shorten the prompt, run independent searches in parallel, use a smaller model to route, and cut agent steps. Streaming does not shorten the tool round trip or the total time. I would report time to first token and total time separately.

**31. How do you pick a model?**

Define the bar on the eval set. Try cheaper models first. Keep the cheapest that clears the bar. Re-test when a model version changes. Public leaderboards are not my traffic. I route only when a cheap model handles most cases and a check sends the hard ones up. In the lab, a primary call over a zero budget falls back to `fake-fallback` and raises `cost_over_budget` and `fallback_used`.

**32. Does schema-valid JSON mean the values are right?**

No. I validate the schema, and I still check the content. A missing currency raises a schema error in the lab. An amount of 9000 is valid JSON and is still queued by the rule.

## System design and the customer

**33. Design a bot over a few thousand internal documents.**

I ask who asks, what a wrong answer costs, and who may see which document. Then: metadata and permissions on each chunk, hybrid search, a grounded prompt that can abstain and must cite, an eval set from real tickets before launch, traces, and a path to a person. For a first version I cut the agent loop and the reranker. I ship the measured search first.

**34. Tell me about a failure you diagnosed.**

The paraphrase. "What do we charge to send money abroad?" retrieved the KYC policy, not the wire fee, because the words did not overlap. I did not touch the prompt. I looked at the top hit, saw the wrong chunk, and the expanded query retrieved `operations-manual#wire-fees`. The prevention is the labeled question staying in the set. A second failure: a plan that quotes the fee before it sees the invoice answers 0 AED, while ReAct answers 20 AED, because the fee depends on the lookup.

**35. The customer wants same-day withdrawals, and staff paste passports into a chatbot. What do you do?**

I sit with the person who releases a withdrawal and write down the checks they already perform. Those become rules. I refuse to automate a sanctions hit, an amount at or above 5000, a missing beneficiary, any case where the model and the rules disagree, and sending a passport or a national id to a model vendor. The metric is the share of complete withdrawals under 5000 that settle the same day, and a skip-the-queue count that stays at zero. I label thirty past cases, including five jailbreaks and five missing beneficiaries, before I build the feature.

**36. Design a tool-using agent that looks up an order and issues a refund.**

Tools have schemas. Arguments are validated before the call. The refund amount must be greater than zero and no greater than the original charge, or I reject without calling the model. The only write path is the gate, so 6000 on an original 8000 is queued, not written. The same idempotency key cannot write a second refund. If the lookup succeeds and the refund call times out, replay uses the same key. I log every tool call.

**37. They ask about MCP, LangGraph, Pinecone, or fine-tuning as if you have shipped them.**

I have not shipped those. I have a loop and the same loop as a two-node graph. LangGraph adds checkpoints and a resume point. I would put that checkpoint before a write, not before a read. Pinecone would replace the in-memory index. The labeled questions and the recall number would stay. I would not fine-tune until retrieval and the rules were measured. A wrong top chunk is not fixed by training.

## From your own work, without internal detail

**38. Where is the Go they asked for?**

Production Go Lambdas for delivery and the call centre: time slots, busy and offline status, order history, and delivery status. I co-built them. I compared them with the older Lambdas before traffic moved. I do not call that a solo design.

**39. How does your payments work connect to this lab?**

The production risk I already handle is a webhook that must not capture twice and a failure I can trace. The lab puts an untrusted extractor in front of that same shape: an idempotency key, a human queue above a limit, and a replay that does not deliver twice. I do not recite gateway payloads in an interview.

## Do not say

- That Harbor Ledger processed real payments, or that the synonym list is an embedding model.
- That you have production LangGraph, Pinecone, Kubernetes at the Telnyx bar, Kafka at partition scale, SIP, or GPU serving.
- That you mentored a team, unless you have one specific example.
- Ticket text, customer data, or employer request bodies.
