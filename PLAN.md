---
title: DocuGuard — Project Plan
created: 2026-09-28
type: project
status: active
tags: [ai-engineer, portfolio, document-intelligence, llmops, flagship]
---

# DocuGuard — Project Plan

## Non-negotiable standard

DocuGuard will be a long-running flagship, not a one-session demo. No phase is
marked complete merely because a happy-path UI works. Every model-backed claim
needs an evaluation set, a metric, and a documented limitation.

## Scope boundaries

- Use public, licensed documents and synthetic documents only where necessary.
- Do not present the system as legal, financial, or compliance advice.
- LLMs may extract, summarize, and retrieve evidence; they do not make final
  business decisions.
- Human review is a core workflow, not a decorative button.

## Milestones

- [x] **0. Product and data contract** — licensed sources, canonical schema,
  evaluation splits, acceptance gates, reviewer workflow, and abuse cases are
  defined in [`docs/data-contract.md`](docs/data-contract.md) and
  [`docs/reviewer-workflow.md`](docs/reviewer-workflow.md).
- [~] **1. Ingestion foundation** — FastAPI application, environment-based
  configuration, Docker Compose development/test PostgreSQL instances, async
  session lifecycle, `DocumentBundle` migration, and isolated integration
  tests are complete. Object-storage abstraction, document metadata, background
  jobs, file validation, and OCR/layout baseline remain.
- [x] **2. Extraction system** — schema-constrained field extraction
  (`StructuredDocumentExtractor`, strict JSON Schema) and provenance spans
  (evidence text per field) are complete. Extraction evaluation set against
  CORD is complete: [`app/scripts/evaluate_cord.py`](app/scripts/evaluate_cord.py)
  reports held-out test accuracy of 100% on `total` (n=95), 100% on
  `document_type`, and a 19% supplier_name flag rate for human review (CORD
  has no ground truth for supplier_name/document_number/currency, so those
  are reported as flags/enrichment, not scored — see the report's own
  `limitations` field). Confidence calibration is complete: on a 100-sample
  validation run, `total`'s stated confidence tracks its actual accuracy
  closely in the dominant 0.9-1.0 bucket (92/98 samples, 98.9% actual
  accuracy) — the model is not overconfident there. The 0.7-0.9 bucket has
  only 2 samples (50% accuracy), too few to draw a conclusion from; this is
  noted as a limitation in the report rather than treated as a finding.
- [~] **3. Reconciliation engine** — deterministic cross-document rules,
  discrepancy taxonomy, reviewer queue, corrections, and audit events.
  Prerequisite closed: structured extraction was previously only reachable
  through standalone scripts (`extract_fields.py`, `evaluate_cord.py`) and
  never persisted, so there was no stored per-document field data for
  documents in the same bundle to compare against each other. The ingestion
  worker (`document_processor.py`) now runs `StructuredDocumentExtractor`
  after text extraction succeeds and persists the result to
  `document_field_extractions` (one row per document, exposed via
  `GET /bundles/{id}/documents/{id}`). Extraction is skipped when OCR is
  required (no usable text) or no extractor is configured (missing API key).
  Cross-document comparison rules, discrepancy taxonomy, and the reviewer
  queue remain.
- [ ] **4. Grounded policy assistant** — hybrid retrieval, reranking, cited
  responses, adversarial retrieval tests, and access-aware tooling.
- [ ] **5. LLMOps and security** — prompt/model/version registry, traces,
  quality/cost/latency dashboards, PII redaction, prompt-injection tests, and
  regression gates.
- [ ] **6. Product delivery** — reviewer UI, API documentation, Docker
  Compose, CI/CD, deploy, model card, data card, architecture decision records,
  and a reproducible demo dataset.
- [ ] **7. External validation** — get feedback from at least two people who
  were not involved in development; turn their feedback into issues and ship
  fixes.

## First acceptance criteria

Before writing application code, we must be able to answer:

1. Which dataset is legally usable and what fields are its ground truth?
2. What is the business cost of a false approval versus an unnecessary review?
3. Which documents should be compared, and which mismatch rules are
   deterministic?
4. Which output requires a human reviewer regardless of model confidence?
5. What metric decides whether an iteration improved the system?
