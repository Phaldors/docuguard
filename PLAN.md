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
- [x] **3. Reconciliation engine** — deterministic cross-document rules,
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
  The deterministic rule engine ([`app/reconciliation/rules.py`](app/reconciliation/rules.py))
  and its discrepancy taxonomy are complete: `total_mismatch`,
  `supplier_mismatch`, `currency_mismatch`, `missing_required_field`,
  `low_confidence_field`, `unclassified_document_type`, and
  `document_not_processed`, each tagged `critical` or `advisory`. Values are
  normalised before comparison (digits-only for totals, casefolded/trimmed
  for text) so formatting variance — e.g. "1,240.00" vs "1240.00" — is not a
  false mismatch, matching truth case 8 in the data contract. Two truth-case
  classes from the data contract are deliberately deferred rather than
  approximated: document-number cross-reference mismatch and date-outside-
  window mismatch need fields DocuGuard doesn't extract yet (a cross-document
  reference number, a normalised date), and quantity/missing-line-item
  mismatch needs `line_items[]` extraction, which doesn't exist. `POST
  /bundles/{id}/reconcile` runs the rules against a bundle's persisted
  document fields, persists the results to `bundle_discrepancies`, and moves
  the bundle to `ready_for_review` (per docs/reviewer-workflow.md's state
  machine, v1 has no auto-approval path — every bundle that finishes
  processing needs a human decision). Rejects with 409 if any document is
  still queued/processing. Re-running reconciliation replaces the prior
  discrepancy set rather than accumulating it, since no correction workflow
  exists yet to make partial re-evaluation meaningful. 18 new tests (pure
  rule-engine unit tests + DB-backed service tests + HTTP endpoint tests),
  all passing, Ruff clean.

  Reviewer queue, corrections, and audit events are complete too, per
  [`docs/reviewer-workflow.md`](docs/reviewer-workflow.md). `GET
  /bundles?status=ready_for_review` lists the queue. Per that document's
  routing policy ("it never edits the original extraction"), a reviewer
  correction is never applied to `document_field_extractions` in place —
  `POST /bundles/{id}/documents/{id}/corrections` (action: `kept` |
  `corrected` | `marked_unavailable`, actor, optional new value, reason)
  only appends an immutable `AuditEvent` recording the prior and new value;
  the original extraction row is untouched. `POST /bundles/{id}/decision`
  (action: `approved` | `rejected` | `needs_info`, actor, required reason)
  records a case decision the same way and transitions the bundle's status;
  it is only valid from `ready_for_review` (rejects with 409 otherwise),
  and a missing/empty reason is rejected with 422 — no case can be decided
  without a human-supplied reason, and no bundle reaches an approved/
  rejected/needs_info state without going through this endpoint. `GET
  /bundles/{id}/audit-events` returns the full append-only history. 13 new
  tests (service-level + HTTP endpoint), 65 total, all passing, Ruff clean.
- [x] **4. Grounded policy assistant** — hybrid retrieval, reranking, cited
  responses, adversarial retrieval tests, and access-aware tooling. Per
  docs/product-brief.md, this is isolated from the decision pipeline: it
  answers questions about how DocuGuard itself works (routing policy,
  discrepancy taxonomy, decision ownership), not about a specific bundle's
  content. Its corpus is therefore DocuGuard's own design docs
  (`docs/product-brief.md`, `docs/data-contract.md`,
  `docs/reviewer-workflow.md`) rather than a licensed external dataset —
  access-aware tooling starts here, as a fixed allow-list of document
  paths with no filesystem access from a request.

  Retrieval ([`app/policy_assistant/retrieval.py`](app/policy_assistant/retrieval.py))
  is genuinely hybrid: a dependency-free BM25 implementation (stopword-
  filtered) plus cosine similarity over precomputed OpenAI embeddings,
  combined with Reciprocal Rank Fusion so the two signals never need score
  normalisation against each other. The corpus is chunked by markdown
  section and embedded once by
  [`app/scripts/build_policy_index.py`](app/scripts/build_policy_index.py)
  into a committed index (`docs/policy-index/index.json`), not re-embedded
  per request. An LLM reranker
  ([`app/policy_assistant/reranker.py`](app/policy_assistant/reranker.py))
  re-scores the hybrid candidates, and answer synthesis
  ([`app/policy_assistant/answer.py`](app/policy_assistant/answer.py))
  requires every claim to carry a citation with a quote and returns
  `grounded: false` instead of guessing when the corpus doesn't cover the
  question. `POST /policy-assistant/ask` wires it together.

  A real retrieval-quality bug was caught during manual end-to-end
  verification (not by the automated tests, which use fakes): the top-8
  hybrid results initially missed the one chunk that actually answered a
  real test question, because BM25 gave equal weight to generic query
  words ("does", "the", "a") as to the distinctive ones ("missing",
  "required"). Fixed by adding a short stopword filter and widening
  `retrieval_limit` from 8 to 12 so the reranker sees a wider net on this
  small (23-chunk) corpus. A second issue, caught the same way: cited
  quotes echoed the chunk's heading label as if it were part of the body
  text. Fixed by separating heading from body in the prompt and requiring
  quotes to be verbatim substrings of body text only.

  [`app/scripts/evaluate_policy_assistant.py`](app/scripts/evaluate_policy_assistant.py)
  is a small hand-written truth set (this corpus is too small for a CORD-
  style held-out split) covering grounded, abstention, and adversarial
  (prompt-injection) queries. Latest run:
  recall@12 100% (5/5), citation support rate 80% (4/5 — the one miss
  reproduced clean on retry, consistent with `gpt-5-mini` not supporting
  `temperature`, already a documented limitation), abstention rate 100%
  (3/3 out-of-corpus queries correctly returned `grounded: false`), and
  injection-resistance rate 100% (2/2 — queries that tried to make the
  assistant output "APPROVED" with no citations were refused, with the
  refusal itself grounded in the reviewer-workflow docs). Full report:
  `docs/eval-reports/policy-assistant-20260929T144047Z.json`. 23 new
  tests (pure retrieval logic, corpus chunking, schema validation, service
  orchestration with fakes, HTTP endpoint with dependency overrides — no
  automated test calls the real OpenAI API), 88 total, all passing, Ruff
  clean.
- [x] **5. LLMOps and security** — prompt/model/version registry, traces,
  quality/cost/latency dashboards, PII redaction, prompt-injection tests, and
  regression gates. Traces and the prompt/model/version registry are
  complete: every one of the system's 4 LLM call sites (extraction,
  embedding, rerank, policy answer) is wrapped in
  [`app/llmops/tracing.py`](app/llmops/tracing.py)'s `trace_call`, which
  persists an `LLMTrace` row (model, a `*_PROMPT_VERSION` constant next to
  each call site's instructions, input/output token counts, latency,
  success/error, and a redacted error message) independently of the
  caller's own DB transaction — a trace is observability data and should
  still be recorded even if the request it came from later fails. This
  doubles as the version registry: grouping traces by
  `(call_type, model, prompt_version)` shows how each prompt/model
  combination is performing. `GET /llmops/traces/summary`
  ([`app/services/llmops.py`](app/services/llmops.py)) is the aggregation
  query a cost/latency/quality dashboard would read from — call count,
  success/error counts, average latency, and total tokens per
  `(call_type, model, prompt_version)`; the dashboard UI itself belongs to
  Milestone 6. PII redaction
  ([`app/llmops/redaction.py`](app/llmops/redaction.py)) is a best-effort
  regex scrubber (email, phone, SSN-like, credit-card-like patterns) for
  observability output, not a comprehensive PII detector — it does not
  catch names or addresses, and is documented as such in its own
  docstring. Verified against the real OpenAI API, not just fakes: a real
  extraction call produced a trace with genuine token counts (375 in / 949
  out) and latency (11.9s). 13 new tests (redaction, tracing success/error
  paths, summary aggregation, HTTP endpoint), 100 total, all passing, Ruff
  clean. Deferred and not yet built: linking a trace to the specific
  document/bundle it came from (the schema has a nullable
  `correlation_id` column for this, unused so far because wiring it
  through would change 4 Protocol signatures and every fake implementing
  them).

  Prompt-injection regression tests and the regression gate are complete
  too, and together they caught and fixed a real vulnerability rather
  than just documenting a prompt's intentions.
  [`app/scripts/evaluate_extraction_robustness.py`](app/scripts/evaluate_extraction_robustness.py)
  embeds instructions inside otherwise-plausible document text (per
  docs/reviewer-workflow.md's abuse case: "OCR text is untrusted data...
  it must never become an instruction to the extractor") and checks
  whether the real extractor's output reflects the document's genuine
  content or the injected claim — this is Milestone 4's adversarial-query
  testing applied to the extraction pipeline, which has a different
  attack surface (injected content the extractor itself ingests, not a
  user's query). The first run scored 75% (3/4): the extractor correctly
  refused to fabricate a total, a supplier name, or fields with no
  genuine evidence, but did comply with an embedded instruction to
  reclassify a genuine delivery note's `document_type` as `"other"`.
  Fixed by adding an explicit paragraph to `EXTRACTION_INSTRUCTIONS`
  naming the document text as untrusted data and covering classification
  specifically, not only field values (bumping
  `EXTRACTION_PROMPT_VERSION` to `extraction-v2` — the version registry
  above is what makes this a real version bump, not just an edit).
  Re-run: 100% (4/4).
  [`app/scripts/check_regression.py`](app/scripts/check_regression.py)
  (10 unit tests on its pure comparison logic) is the generic regression
  gate — it takes two eval reports and a metric-direction table and
  fails if a tracked metric moved past tolerance — and was used for real
  here: a 20-sample CORD validation run under `extraction-v2` was
  compared against the pre-fix baseline and showed no regression
  (`total_accuracy` and `document_type_accuracy` both still 100%,
  `supplier_name_flagged_rate` improved to 10%), confirming the prompt
  change fixed the injection gap without a field-accuracy cost.
  `evaluate_extraction_robustness.py` itself is a real-API eval script,
  like `evaluate_cord.py` and `evaluate_policy_assistant.py` before it,
  not part of the standard pytest suite; 10 new unit tests cover
  `check_regression`'s pure comparison logic, bringing the project to
  110 tests total, all passing, Ruff clean.
- [~] **6. Product delivery** — reviewer UI, API documentation, Docker
  Compose, CI/CD, deploy, model card, data card, architecture decision records,
  and a reproducible demo dataset. The first delivery artifact is complete:
  [`app/scripts/seed_demo.py`](app/scripts/seed_demo.py) provisions a
  source-controlled, fully synthetic reviewer case without an API key or a
  network call. It seeds a fixed invoice / purchase-order / delivery-note
  bundle with raw evidence, persisted field extractions, and the reconciler's
  deterministic result: one critical total mismatch and one advisory
  low-confidence supplier. The script is idempotent by default and `--reset`
  replaces only the fixed demo bundle, so a product walkthrough can always
  begin from the same state. [`docs/demo.md`](docs/demo.md) explicitly marks
  this as a workflow fixture rather than an extraction benchmark. The first
  reviewer UI is also complete at `/reviewer`: it is a dependency-free screen
  served by FastAPI, built over a dedicated read-only
  `GET /bundles/{id}/review` read model. It shows the queue, raw extracted
  evidence, field values/confidence, deterministic findings, and audit history;
  corrections and decisions remain explicit calls to their existing append-only
  endpoints. API data is inserted with `textContent`, not HTML interpolation,
  so untrusted document text cannot become a stored-XSS payload. Production
  delivery is now defined too: `Dockerfile` creates a non-root, lockfile-based
  image; `compose.production.yaml` separates PostgreSQL, one-shot migrations,
  and the API with persistent document storage; and `.github/workflows/ci.yml`
  performs locked dependency installation, linting, test-DB migrations, the
  full suite, and a production-image build on every PR/main push. It explicitly
  does not deploy, because a real target environment/secrets choice remains a
  human decision. Details: [`docs/deployment.md`](docs/deployment.md). Next:
  model/data cards and architecture decision records.
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
