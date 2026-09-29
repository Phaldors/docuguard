# API guide

Interactive OpenAPI documentation is available at `/docs` while the server is
running. This guide describes the intended workflow and state boundaries.

## Workflow endpoints

- `POST /bundles` starts a case with a tenant ID.
- `POST /bundles/{bundle_id}/documents` validates and stores one PDF.
- `GET /bundles/{bundle_id}/documents/{document_id}` returns metadata plus
  persisted extraction/field summaries when available.
- `POST /bundles/{bundle_id}/reconcile` runs deterministic checks only after
  document processing has finished. It moves the bundle to `ready_for_review`;
  it never approves a case.
- `GET /bundles?status=ready_for_review` is the review queue.
- `GET /bundles/{bundle_id}/review` is the reviewer read model: bundle status,
  documents, extracted text, field summaries, discrepancies, and audit events.
- `POST /bundles/{bundle_id}/documents/{document_id}/corrections` appends a
  field-review event. It does not mutate the original extraction.
- `POST /bundles/{bundle_id}/decision` appends a human decision and requires a
  non-empty reason.
- `GET /bundles/{bundle_id}/audit-events` returns the append-only history.

## Model and observability endpoints

- `POST /policy-assistant/ask` answers only from the versioned policy corpus
  and either cites evidence or returns `grounded: false`.
- `GET /llmops/traces/summary` groups model traces by call type, model, and
  prompt version for latency/cost/error inspection.

## Error conventions

Malformed input is returned as `422`; unknown resources as `404`; a state
transition that is not currently valid, such as reconciling an in-flight bundle
or deciding a non-reviewable bundle, is returned as `409`. Clients should treat
these as workflow signals rather than retrying blindly.
