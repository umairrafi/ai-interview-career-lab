# Discovery drill

Use this for Cohere, both qlub roles, and the Provectus redesign round. Provectus still wants eight or more years and a system that already ran for a customer. The drill is the practice, not an application.

## The brief

The operations lead at Harbor Ledger says: "Clients wait three days for withdrawals. Put an AI on it so payments go out the same day. The team already pastes passport images into a chatbot."

They have not said which withdrawals, what "same day" includes, or what the chatbot is allowed to see.

## What you do in the first meeting

Sit with the person who actually releases a withdrawal. Write down the checks they already perform: beneficiary present, amount, currency, sanctions status, and whether the amount is inside the client's mandate. Those checks become the rules. The model does not replace them.

Refuse, in the meeting, to automate any of these:

- A sanctions hit.
- An amount at or above 5000 AED.
- A missing beneficiary.
- A case where the model says approved and the rules disagree.
- Sending a passport image or a national id to a model vendor.

## Success metric

Share of withdrawals under 5000 AED, with a complete beneficiary and a confidence of at least 0.85, that settle the same day. Beside it, a count of writes that skipped the human queue. That count has to stay at zero. Speed without the zero is not a success.

## The eval, before the feature

Thirty past withdrawals, labeled accept, queue, or reject by the operator. Include five cases whose text says to skip the queue, and five with a missing beneficiary. Ship only if safety on that set is 1.0 and agreement with the operator is at least the baseline you write down before you change a prompt. Lab 5 is the small version of this harness. Lab 4 is the gate the harness calls.

## What you would build

A webhook receives the withdrawal. A correlation id ties the request, the decision, and the ledger row. The prompt contains the client id, the amount, the currency, and the reason. It does not contain the national id. The gate accepts, rejects, or queues. A vendor timeout fails the job before a write. Replay uses the same idempotency key. Labs 4, 6, and 7 are that system at practice scale.

## The sentence to close on

"I will measure same-day settlement for the low-value, complete cases, and I will not ship a path that can write when the rules say queue."
