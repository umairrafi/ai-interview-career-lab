"""Local retrieval. Paragraph chunks against whole-document chunks."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+")
DATA = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def slugify(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def load_corpus() -> list[tuple[str, str]]:
    docs = []
    for path in sorted((DATA / "corpus").glob("*.md")):
        docs.append((path.stem, path.read_text()))
    return docs


def chunk_whole(doc_id: str, text: str) -> list[Chunk]:
    return [Chunk(id=doc_id, doc_id=doc_id, text=text)]


def chunk_paragraphs(doc_id: str, text: str) -> list[Chunk]:
    parts = re.split(r"^## ", text, flags=re.M)
    chunks = []
    for part in parts[1:]:
        lines = part.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        chunks.append(
            Chunk(
                id=f"{doc_id}#{slugify(heading)}",
                doc_id=doc_id,
                text=f"{heading}\n{body}",
            )
        )
    return chunks


class Index:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        doc_tokens = [tokenize(chunk.text) for chunk in chunks]
        df: Counter[str] = Counter()
        for tokens in doc_tokens:
            df.update(set(tokens))
        count = max(1, len(chunks))
        self.idf = {term: math.log((1 + count) / (1 + freq)) + 1 for term, freq in df.items()}
        self.vectors = [self._vector(tokens) for tokens in doc_tokens]

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {term: freq * self.idf.get(term, 1.0) for term, freq in counts.items()}

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        query_vector = self._vector(tokenize(query))
        scored = sorted(
            self.chunks,
            key=lambda chunk: _cosine(query_vector, self.vectors[self.chunks.index(chunk)]),
            reverse=True,
        )
        return scored[:k]


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    dot = sum(left[term] * right[term] for term in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def build_index(mode: str) -> Index:
    chunker = chunk_paragraphs if mode == "paragraphs" else chunk_whole
    chunks: list[Chunk] = []
    for doc_id, text in load_corpus():
        chunks.extend(chunker(doc_id, text))
    return Index(chunks)


def load_questions() -> list[dict]:
    return json.loads((DATA / "questions.json").read_text())


def precision_at_1(mode: str) -> float:
    index = build_index(mode)
    questions = load_questions()
    hits = 0
    for question in questions:
        top = index.search(question["query"], k=1)[0]
        if top.id in question["relevant"]:
            hits += 1
    return hits / len(questions)


def recall_at_k(mode: str, k: int = 3) -> float:
    """Share of questions whose labeled chunk appears anywhere in the top k."""
    index = build_index(mode)
    questions = load_questions()
    hits = 0
    for question in questions:
        found = {chunk.id for chunk in index.search(question["query"], k=k)}
        if found & set(question["relevant"]):
            hits += 1
    return hits / len(questions)


SYNONYMS = {
    "abroad": ["international"],
    "overseas": ["international"],
    "charge": ["fee"],
    "send": ["wire"],
    "money": ["wire"],
}

PARAPHRASE = "what do we charge to send money abroad"
PARAPHRASE_HIT = "operations-manual#wire-fees"


def expand_query(query: str) -> str:
    extra: list[str] = []
    for token in tokenize(query):
        extra.extend(SYNONYMS.get(token, []))
    return f"{query} {' '.join(extra)}".strip()


def paraphrase_tops() -> tuple[str, str]:
    index = build_index("paragraphs")
    sparse = index.search(PARAPHRASE, k=1)[0].id
    expanded = index.search(expand_query(PARAPHRASE), k=1)[0].id
    return sparse, expanded
