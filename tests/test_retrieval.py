from ledgerlab.retrieval import build_index, precision_at_1


def test_paragraph_chunks_raise_precision():
    coarse = precision_at_1("whole")
    fine = precision_at_1("paragraphs")
    assert coarse == 0.5, _tops("whole")
    assert fine == 1.0, _tops("paragraphs")
    assert fine > coarse


def _tops(mode: str) -> str:
    from ledgerlab.retrieval import load_questions

    index = build_index(mode)
    lines = []
    for question in load_questions():
        top = index.search(question["query"], k=1)[0]
        lines.append(f"{question['id']}: {top.id}")
    return ", ".join(lines)


def test_recall_cannot_find_a_passage_that_was_not_indexed():
    from ledgerlab.retrieval import recall_at_k

    assert recall_at_k("whole", 3) == 0.5
    assert recall_at_k("paragraphs", 3) == 1.0


def test_sparse_search_misses_a_paraphrase():
    from ledgerlab.retrieval import PARAPHRASE_HIT, paraphrase_tops

    sparse, expanded = paraphrase_tops()
    assert sparse != PARAPHRASE_HIT, sparse
    assert expanded == PARAPHRASE_HIT, expanded
