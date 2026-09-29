# Data card

## Purpose and separation

DocuGuard deliberately separates data used for model evaluation from data used
to demonstrate reconciliation and review. One dataset cannot credibly prove
both receipt-field extraction and an invoice/purchase-order/delivery-note
workflow.

## CORD receipt benchmark

- Source: [CLOVA CORD](https://github.com/clovaai/cord).
- Licence: CC BY 4.0; attribution is retained through this card and the data
  contract.
- Role: held-out semantic receipt-field extraction evaluation.
- Ground truth: annotated OCR text regions and semantic labels.
- Split discipline: prompt work is done against validation data; the official
  test split is held out for the reported test run.
- Limit: Indonesian receipts do not represent a complete invoice,
  purchase-order, and delivery-note workflow.

The dataset itself is not committed to this repository. The committed reports
record evaluation outcomes and limitations without redistributing source data.

## DocLayNet layout checks

- Source: [DocLayNet](https://huggingface.co/datasets/docling-project/DocLayNet).
- Licence: CDLA-Permissive-1.0.
- Intended role: document-layout segmentation and routing robustness checks.
- Limit: it is not used to claim semantic invoice-field accuracy.

No DocLayNet-derived performance claim is currently published in this
repository because a completed, versioned run is not yet present.

## Synthetic reviewer fixture

`app/demo/seed.py` contains a versioned, fully fictional three-document case:
an invoice, purchase order, and delivery note for Northwind Industrial Ltd.
It is seeded directly into the database by `app/scripts/seed_demo.py`, never
sent to an LLM, and has no customer or personal data.

Its fixed expected result is one critical `total_mismatch` (USD 1,240.00 versus
USD 1,300.00) and one advisory `low_confidence_field` (supplier confidence
0.62). The fixture proves that the reviewer workflow and audit model are
repeatable; it is explicitly not an extraction benchmark or an OCR corpus.

## Exclusions and handling rules

- FUNSD is excluded from the public/product path because its stated licence is
  restricted to non-commercial research and education.
- SROIE is excluded until redistribution and portfolio-use permissions are
  verified from an authoritative source.
- No scraped invoices, bank statements, user-provided sensitive files, or API
  keys enter the repository.
- User uploads reside in configured document storage and are excluded by
  `.gitignore` and `.dockerignore`.
- Public demonstrations use only the synthetic fixture. A local real-document
  smoke test is not a public benchmark and must never be committed.

## Known gaps

The synthetic fixture is a single, intentionally small scenario. The larger
seeded generator and formal template-family holdout described in
`docs/data-contract.md` are not implemented yet, so no recall/precision metric
for the full reconciliation truth-case taxonomy is claimed.
