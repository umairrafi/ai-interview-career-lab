# Lab 2. Retrieval

Postings this covers: Cohere (RAG), Danube (RAG), Telnyx (prompt and RAG pipelines, eval harnesses), Globant (chunking and context injection), the agentic role (vector search). This index is local term weights, not a hosted vector database. The metric is the part those postings grade.

Code: [retrieval.py](../src/ledgerlab/retrieval.py). Corpus: [data/corpus](../data/corpus). Questions: [data/questions.json](../data/questions.json).

Four questions have labeled passages. Two answers sit inside one operations manual (the wire fee and the lunch stipend). Two answers are the only section of their own short policy.

Whole-document chunks score **0.5** precision at 1. The top hit for the wire fee is the entire manual, which is not the labeled passage. The two short policies still match, because the whole file is the labeled document.

Splitting on headings scores **1.0** on the same questions. One change. The number moved.

## Interview

**Story.** I indexed the same invented policies two ways and scored precision at 1 on a fixed set of four questions. Whole documents scored 0.5 because the wire fee and the lunch stipend were buried in one manual, so the top hit was a mixed page. Splitting on headings scored 1.0. I would not claim a vector database from this. I would claim that I measured retrieval before I let a model answer from it.

**Number.** Precision@1 moved from 0.5 to 1.0.

**Failure.** The coarse index answered "domestic wire fee" with the whole operations manual, which also contains the lunch stipend and the parking rules. That hit is not the labeled passage.
