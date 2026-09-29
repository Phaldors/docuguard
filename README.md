# DocuGuard

**A secure document-intelligence and human-review platform for enterprise
operations.**

DocuGuard ingests scanned and digital business documents, extracts structured
fields, cross-checks those fields against related documents, and routes
uncertain cases to a human reviewer with evidence and an auditable decision
history.

This is not a generic chat-with-PDF product. It is an AI workflow system where
models assist with extraction and explanation, while deterministic rules and
human approval own consequential decisions.

The deployed portfolio demo opens directly into the reviewer workflow at `/`.

## Intended workflow

1. A user uploads a document bundle: invoice, purchase order, and delivery
   note.
2. The ingestion pipeline stores the source, runs OCR/layout parsing, and
   classifies document type.
3. Structured extraction returns fields with source spans and confidence.
4. A rules engine checks cross-document consistency: supplier, amount, date,
   currency, and purchase-order reference.
5. High-confidence, rule-compliant cases can be marked ready for approval;
   uncertain or conflicting cases enter a reviewer queue.
6. A reviewer sees the source evidence, model output, rules triggered, and can
   approve, reject, or correct the result. Each action is audited.

## What this project must prove

- Python backend design, async document processing, APIs, SQL, and Docker.
- OCR/VLM/LLM integration without handing critical decisions to an LLM.
- Hybrid retrieval and grounded answers for operational-policy questions.
- Evaluation of extraction, retrieval, and workflow quality.
- Secure-by-design handling: PII redaction, role separation, audit history,
  and adversarial-input testing.
- Production thinking: versioned datasets/models/prompts, traces, latency,
  cost, monitoring, rollback, and CI quality gates.

## Project status

Milestones 0–5 are complete: ingestion, structured extraction,
cross-document reconciliation, reviewer audit actions, a grounded policy
assistant, and LLM tracing/security controls. The next product-delivery work
starts with a reproducible reviewer demo; see [the demo guide](docs/demo.md).

Run the API from the project directory:

```bash
uv run uvicorn app.main:app --reload
```

After uploading a PDF, run one queued extraction job in a separate terminal:

```bash
uv run python -m app.workers.run_once
```

See [PLAN.md](PLAN.md) and [product brief](docs/product-brief.md) for the
full product scope. Production container/CI instructions are in
[deployment.md](docs/deployment.md); the API guide, model card, data card, and
architecture decisions live under [`docs/`](docs/). A deliberately limited
Render portfolio-demo Blueprint is documented in [render.md](docs/render.md).
