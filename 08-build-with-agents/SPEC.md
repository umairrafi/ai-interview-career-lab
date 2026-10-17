# Refund request

Status: implemented in `src/ledgerlab/refund.py`. Acceptance tests are in `tests/test_refund.py`.

## Done means

- The caller passes the original write key, a refund amount, a reason, and an idempotency key.
- An unknown original is rejected. Nothing is written.
- The amount must be greater than zero and no greater than the original charge. Otherwise reject, and do not call the model.
- A refund that passes that check is a normal gate packet with `document_type` of `refund`. The gate still queues amounts at or above 5000, and confidence below 0.85.
- The same idempotency key does not write a second refund.
- The feature file does not call a card API, `wire_money`, or `Store.commit`. The only write path is `apply`.

## Out of scope

- Moving money at a real gateway.
- Sending the original national id to a model.
