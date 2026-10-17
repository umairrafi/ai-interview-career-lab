# Lab 8. Build with agents

Postings this covers: qlub's AI Engineer role (you write the spec, the acceptance tests, and the evals; agents implement; you prove the result), Globant's .NET AI Coder role (a personal method for catching AI-generated defects; their 7-year .NET line is separate), spiderSilk (AI tools in daily work, with review).

Spec: [SPEC.md](SPEC.md). Implementation: [refund.py](../src/ledgerlab/refund.py). Checklist: [review.py](../src/ledgerlab/review.py).

The habit this lab practices:

1. Write the spec and the acceptance tests first. "Done" is a refund that stays inside the original charge and still passes the write gate.
2. Let an agent implement against that spec. Review the diff, not the model's explanation.
3. Run the checklist on the feature file and its tests.

The checklist flags three things:

- A hallucinated API: `ledgerlab.payments.charge_card`, `stripe.Charge.create`, or `wire_money(`.
- A test named `test_` that contains no `assert` and no `pytest.raises`.
- A `commit` in the feature file that does not go through `apply`.

The shipped refund file passes the checklist. A planted bad diff fails all three kinds. A historical 8000 AED charge refunded for 6000 is queued, because 6000 is inside the original amount and still over the human threshold. A refund of 2000 against an original 1000 is rejected before the model is called.

## Interview

**Story.** I treated the refund as a spec and a set of acceptance tests, then checked the diff. The amount has to sit inside the original charge, and the only write path is the same gate as any other payment. The checklist is what I run on agent-written code: an API that does not exist, a test that asserts nothing, and a commit that skips the gate. I can show the planted bad diff failing and the shipped file passing.

**Number.** A historical 8000 AED charge, refunded for 6000, is queued and not written.

**Failure.** The checklist catches `charge_card`, a test with no assert, and a `commit` that bypasses `apply`. Any one of those blocks the merge.
