# Reproducible reviewer demo

This fixture demonstrates the product workflow, not extraction accuracy. It is
fully synthetic, versioned in source control, and makes no OpenAI request.
The seed writes an already-extracted invoice, purchase order, and delivery note
directly to the configured database so every reviewer demo starts with the
same evidence, confidence values, and reconciliation outcome.

## Scenario

`docuguard-demo` contains three documents from **Northwind Industrial Ltd.**:

- invoice `INV-2026-0042`: total **USD 1,240.00**;
- purchase order `PO-2026-0917`: total **USD 1,300.00**;
- delivery note `DN-2026-077`: supplier extraction confidence **0.62**.

The reconciler therefore creates exactly two findings:

1. a **critical** `total_mismatch` between the invoice and purchase order;
2. an **advisory** `low_confidence_field` on the delivery note's supplier.

The case is always routed to `ready_for_review`. It is never auto-approved.

## Run it locally

Start PostgreSQL and apply migrations first:

```bash
docker compose up -d
uv run alembic upgrade head
```

Then create (or inspect) the fixed case:

```bash
uv run python -m app.scripts.seed_demo
```

To replace only this fixture with a clean copy, use:

```bash
uv run python -m app.scripts.seed_demo --reset
```

`--reset` affects the single fixed demo bundle only; it does not clear any
other tenant's data. Start the API with `uv run uvicorn app.main:app --reload`
and open `http://127.0.0.1:8000/reviewer`. The dependency-free reviewer screen
loads the queue, shows extracted evidence and confidence, exposes deterministic
findings, and writes explicit correction/decision events to the audit trail.

## Deliberate limits

The records use `method=demo_fixture` and placeholder storage keys because this
is a deterministic reviewer-flow fixture, not an uploaded binary corpus. Do
not quote it as evidence of PDF/OCR/LLM extraction performance; use the CORD
and robustness reports in `docs/eval-reports/` for those claims.
