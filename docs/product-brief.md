---
title: DocuGuard Product Brief
created: 2026-09-28
type: product-brief
status: draft
---

# Product brief: DocuGuard

## Problem

Operations teams review related business documents manually. A missed mismatch
between an invoice and purchase order can create payment, reconciliation, and
audit risk. Straight OCR is insufficient: the system must understand document
type, extract fields with evidence, compare records, communicate uncertainty,
and preserve reviewer decisions.

## Primary user

An operations reviewer handling invoice-document bundles. They need to answer:

- What was extracted, from which page/region, and how confidently?
- Does this invoice match its purchase order and delivery note?
- Which rule or piece of evidence created the risk flag?
- Can I correct the output without silently overwriting the original record?

## Core decisions

- **Extract a field:** model-owned; records value, document span, confidence,
  and model version.
- **Flag a mismatch:** deterministic-rule-owned; records field values, rule
  identifier, and threshold.
- **Approve or reject a case:** human-reviewer-owned; records reviewer ID,
  reason, and timestamp.
- **Answer a policy question:** retrieval + LLM; records cited source chunks
  and access scope.

## Deliberate exclusions for v1

- No automatic payments, credit decisions, or contractual actions.
- No claims of regulatory compliance.
- No customer PII in the public demo environment.
- No multi-agent orchestration unless a measured workflow requirement demands
  it.

## Architecture at a glance

`Upload API → validation → async OCR/extraction → PostgreSQL + object storage →
rules/reconciliation → reviewer queue → audit log`

The policy assistant is isolated from the decision pipeline:

`policy documents → hybrid retrieval + reranker → cited answer`

## Evaluation families

- Extraction: field-level precision, recall, F1, and confidence calibration.
- Reconciliation: precision/recall by mismatch type and false-review rate.
- Retrieval: Recall@K and citation support rate.
- Workflow: reviewer correction rate, time-to-decision, and trace completeness.
- Reliability: p95 latency, failure rate, cost per document, and regression
  rate across released versions.
