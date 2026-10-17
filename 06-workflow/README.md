# Lab 6. Workflow

Postings this covers: the brokerage role (webhooks, scheduled-style retries, idempotency, correlation ids, replay), Danube (a workflow you can draw), qlub (integrations that keep working when a vendor fails).

Code: [workflow.py](../src/ledgerlab/workflow.py).

The brokerage posting names n8n, Power Automate, or UiPath, and it also accepts a code-based orchestrator. This is that orchestrator. The map below is the same flow in the shape those tools draw.

```text
webhook
  |
  v
same idempotency key? -- yes --> return the existing correlation id
  | no
  v
assign correlation id
  |
  v
reserve vendor slot
  |-- timeout --> status failed, no ledger write
  |-- transient error --> retry, up to 3 attempts
  v
write gate
  |-- reject or queue --> stop, no delivery
  v
deliver once for this correlation id
  |
  v
status written
```

Replay of a failed job resets the attempt count and runs again. Replay of a written job returns the same write and does not deliver a second time. A vendor that fails the first two reserves and succeeds on the third produces one ledger row and three attempts.

A timeout is raised on reserve, before the gate runs, so a dead vendor does not create a ledger row. After the vendor recovers, replay writes once.

## Interview

**Story.** A webhook gets a correlation id, and the same idempotency key does not open a second job. I retry a vendor that fails twice, and the ledger still has one row, because the gate commits under that key and delivery is recorded per correlation id. A timeout fails the job before any write. Replay is how I finish it once the vendor is back. Replay of a job that already wrote does not deliver again.

**Number.** 3 attempts, 1 write, when the vendor fails the first two calls.

**Failure.** The timeout path leaves the ledger empty. I do not retry a timeout inside the same call. Replay is the recovery.
