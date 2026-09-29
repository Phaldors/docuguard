---
title: DocuGuard Data Contract
created: 2026-09-28
type: design
status: approved-for-foundation
tags: [docuguard, data, evaluation, licensing]
---

# Data contract

## Purpose

DocuGuard needs two different kinds of evidence. A real, labelled dataset is
needed to measure document-field extraction honestly. A controlled document
bundle is needed to measure reconciliation rules and reviewer decisions. One
dataset does not credibly provide both.

## Approved v1 sources

### 1. CORD: receipt extraction benchmark

- Source: [CLOVA CORD](https://github.com/clovaai/cord)
- Licence: CC BY 4.0; attribution must be retained in the repository and data
  card.
- Use: evaluate receipt-level semantic field extraction on the held-out test
  split.
- Ground truth: annotated OCR text regions and semantic labels.
- Limitation: it contains Indonesian receipts, not a complete invoice, purchase
  order, and delivery-note workflow. It is an extraction benchmark only.

### 2. DocLayNet: layout robustness checks

- Source: [DocLayNet](https://huggingface.co/datasets/docling-project/DocLayNet)
- Licence: CDLA-Permissive-1.0.
- Use: document-layout segmentation and routing robustness checks.
- Limitation: it is not used to claim semantic invoice-field accuracy.

### 3. Synthetic three-document bundles: reconciliation evaluation

- Source: a deterministic generator versioned in this repository.
- Documents: invoice, purchase order, delivery note.
- Use: control exact ground truth and inject one discrepancy at a time.
- Public-demo policy: fictional vendors, products, IDs, and amounts only; no
  personal or customer data.

## Explicit exclusions

- FUNSD is excluded from the public/product evaluation path because its stated
  licence is restricted to non-commercial research and education.
- SROIE is excluded until its redistribution and portfolio-use licence is
  verified from an authoritative source.
- No scraped invoices, bank statements, or user-provided sensitive documents
  enter the repository or evaluation suite.

## Canonical v1 document schema

Every document gets a versioned `DocumentRecord` with:

- `document_id`, `bundle_id`, `document_type`, `source_kind`, `created_at`
- `supplier_name`, `document_number`, `document_date`, `currency`, `total`
- `line_items[]`: `sku`, `description`, `quantity`, `unit_price`, `line_total`
- `evidence[]`: page, bounding box/span, OCR text, extractor/model version
- `field_confidence`, `review_status`, and immutable audit-event references

The invoice, purchase order, and delivery note share those common fields. No
field is silently normalised over the raw extracted value: both original text
and normalised value are retained.

## Reconciliation truth cases

The synthetic generator must make each case reproducible from a seed and label
the expected outcome. Initial discrepancy classes:

1. matching bundle;
2. total amount mismatch;
3. quantity mismatch;
4. supplier mismatch;
5. document-number mismatch;
6. date outside the permitted window;
7. missing line item; and
8. OCR-like formatting variance that should **not** produce a mismatch.

## Holdout protocol

- CORD: never tune on its official test split. Keep a local validation split
  separate from the held-out test report.
- Synthetic bundles: split by template family and random seed so visually near
  duplicates cannot leak into both validation and test.
- Every reported run records dataset version, generator version/seed range,
  prompt version, model version, configuration hash, timestamp, and commit.

## Baseline acceptance thresholds

These are starting gates, not claims of production readiness. They will be
revised only through a documented decision record.

- Extraction: macro field-level F1 >= 0.85 on the CORD held-out report.
- Reconciliation: recall >= 0.95 for injected critical mismatches; no false
  auto-approval is allowed because v1 has no auto-approval action.
- Human-review routing: all low-confidence extraction and all critical rule
  flags enter review.
- Traceability: 100% of evaluated fields have source evidence or an explicit
  `evidence_unavailable` reason.

## Decision ownership

- Extraction can propose a value.
- Rules can flag a discrepancy.
- Only a human reviewer can approve, reject, or override a case.

This contract deliberately makes the system useful without pretending it can
make financial decisions autonomously.
