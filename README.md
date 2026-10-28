# DocuGuard

**A secure document-intelligence and human-review platform for enterprise
operations.**

DocuGuard ingests scanned and digital business documents, extracts structured
fields with source-span evidence, cross-checks those fields against related
documents in a bundle, and routes uncertain or conflicting cases to a human
reviewer with an auditable, append-only decision history.

This is not a generic chat-with-PDF product. Models assist with schema-constrained
extraction and grounded policy Q&A, while **deterministic rules and human
approval own consequential decisions**.

---

## Highlights & Measured Results

1. **Models propose; deterministic rules and humans decide.** `StructuredDocumentExtractor` extracts fields (`supplier_name`, `document_number`, `document_date`, `currency`, `total`) with verbatim source-span evidence and confidence scores. A pure, deterministic reconciliation engine ([`app/reconciliation/rules.py`](app/reconciliation/rules.py)) checks cross-document consistency across invoice, purchase order, and delivery note (`total_mismatch`, `supplier_mismatch`, `currency_mismatch`, `missing_required_field`, `low_confidence_field`, `unclassified_document_type`, `document_not_processed`).
2. **Source-linked reviewer workspace (`/reviewer`).** Clicking a discrepancy or extracted field highlights the verbatim source evidence span in the document viewer (`<mark>` over `textContent` DOM nodes—never `innerHTML`, preventing stored XSS from untrusted OCR text). Reviewer corrections and case decisions (`approved`, `rejected`, `needs_info`) are recorded as immutable, append-only `AuditEvent` rows; original model extractions are never overwritten in place.
3. **Genuine hybrid RAG for operational policy (`/policy-assistant/ask`).** Combines dependency-free stopword-filtered BM25 + OpenAI embedding cosine similarity via Reciprocal Rank Fusion (RRF), followed by an LLM reranker and cited answer synthesis that refuses to guess (`grounded: false`) when a question falls outside the allow-listed corpus.
4. **LLMOps, prompt-injection defense, and regression gating.** All 4 LLM call sites (extraction, embedding, rerank, policy synthesis) are wrapped in `trace_call` ([`app/llmops/tracing.py`](app/llmops/tracing.py)), persisting model, `*_PROMPT_VERSION`, token counts, latency, and PII-redacted errors to PostgreSQL (`GET /llmops/traces/summary`). Adversarial evaluation caught a real v1 classification-hijack bug (3/4 → 4/4 after upgrading to `extraction-v2`), verified against CORD with [`check_regression.py`](app/scripts/check_regression.py).

### Evaluation Summary

Full JSON reports live under [`docs/eval-reports/`](docs/eval-reports/) and scope caveats are documented in the [Model Card](docs/model-card.md) and [Data Card](docs/data-card.md).

| Component / Suite | Dataset / Probe | Metric | Result | Notes & Scope Limits |
| --- | --- | --- | --- | --- |
| **Structured Extraction** | CORD held-out test (`n=95`) | `total` & `document_type` accuracy | **100% (95/95)** | `supplier_name` flagged for review on 19% of samples (CORD lacks supplier/doc-no ground truth; scored as enrichment flags). |
| **Confidence Calibration** | CORD validation (`n=100`) | Actual accuracy in `0.9–1.0` confidence bucket | **98.9% (92/98)** | Only 2 samples fell in `0.7–0.9` (50%); confidence is never used for auto-approval in v1. |
| **Extraction Injection Probe** | Embedded document-text attacks (`n=4`) | Injection resistance (`extraction-v1` → `v2`) | **75% → 100% (4/4)** | `v1` resisted fake totals/suppliers but obeyed an embedded `reclassify as other` command; fixed in `extraction-v2` with zero CORD regression. |
| **Policy Assistant (Hybrid RAG)** | Hand-written truth set (`n=10`: 5 grounded, 3 OOD, 2 adversarial) | Recall@12 / Citation support / Abstention / Injection resistance | **100% / 80% / 100% / 100%** | Small release-gate probe over the 23-chunk design-doc corpus, not a broad external benchmark. |

---

## Architecture & Workflow

```text
Document Bundle (Invoice + PO + Delivery Note)
  │
  ├─► Ingestion Worker ──► PDF Text Parse ──► StructuredDocumentExtractor (strict JSON Schema + evidence spans)
  │                                                  │
  │                                                  ▼
  ├─► Deterministic Reconciler ◄──────────── document_field_extractions (PostgreSQL)
  │     (7 discrepancy rules, normalized comparison)
  │            │
  │            ▼
  ├─► Reviewer Console (/reviewer) ──► Source Evidence Highlight + Append-Only AuditEvents (corrections & decisions)
  │
  ├─► Policy Assistant (/policy-assistant/ask) ──► BM25 + Embeddings ──► RRF ──► LLM Reranker ──► Cited Answer / Abstain
  │
  └─► LLMOps Layer (/llmops/traces/summary) ──► Per-call Tracing + Prompt Version Registry + Regex PII Redaction
```

### Repository Structure & Engineering Quality

- **`app/`**: FastAPI application, async SQLAlchemy 2.0 + Alembic migrations, deterministic reconciliation engine (`app/reconciliation/`), hybrid RAG pipeline (`app/policy_assistant/`), LLMOps tracing & PII redaction (`app/llmops/`), and source-linked reviewer UI (`app/web/`).
- **`tests/`**: **121 automated tests** (unit, DB-backed service integration, HTTP API, and public-demo security boundaries) running against isolated PostgreSQL test state with fake/Protocol LLM doubles, plus Ruff linting in GitHub Actions CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
- **`docs/`**: [Product Brief](docs/product-brief.md), [Data Contract](docs/data-contract.md), [Reviewer Workflow](docs/reviewer-workflow.md), [API Reference](docs/api.md), [Model Card](docs/model-card.md), [Data Card](docs/data-card.md), [Deployment Guide](docs/deployment.md), [Public Demo Security](docs/public-demo-security.md), and [Architecture Decision Records](docs/adr/).

---

## Run Locally

### 1. Reproducible Reviewer Demo (No API Key Required)

[`app/scripts/seed_demo.py`](app/scripts/seed_demo.py) provisions a deterministic, synthetic invoice / purchase-order / delivery-note bundle with raw evidence, extracted fields, and reconciliation findings (one critical total mismatch: `1240.00` vs `1300.00 USD`, and one advisory low-confidence supplier):

```bash
uv sync --locked
docker compose up -d postgres postgres_test
uv run alembic upgrade head
uv run python -m app.scripts.seed_demo --reset
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` (redirects to `/reviewer`). See [ the demo guide ](docs/demo.md) for a step-by-step walkthrough.

### 2. Full Pipeline & Tests

After uploading a PDF bundle, process queued extraction jobs:

```bash
uv run python -m app.workers.run_once
```

Run linting and the full test suite (121 tests):

```bash
uv run ruff check .
uv run pytest -q
```

---

## Known Limitations

- **Text-layer extraction first:** v1 extracts native PDF text and flags image-only documents as `ocr_required`; layout-aware OCR and page/bounding-box provenance coordinates are planned next steps.
- **Deferred truth cases:** Cross-document reference-number matching, date-window validation, and line-item quantity reconciliation are explicitly deferred in [`docs/data-contract.md`](docs/data-contract.md) until those fields are added to the extraction schema.
- **Regex PII scrubbing:** `app/llmops/redaction.py` scrubs emails, phones, SSN-like, and card-like patterns from traces, but does not detect free-text person names or street addresses.

See [PLAN.md](PLAN.md) for the complete milestone log and engineering decisions.
