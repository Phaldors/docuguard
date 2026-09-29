# Model card

## Scope

DocuGuard uses models only to propose structured fields or produce grounded
policy answers. Models never approve, reject, pay, or otherwise make a
consequential business decision. Those operations remain owned by deterministic
rules and a human reviewer.

## Models and roles

### Structured document extraction

- Model: `gpt-5-mini` (configured through `DOCUGUARD_EXTRACTION_MODEL`).
- Input: native PDF text when available; the text is treated as untrusted data.
- Output: strict-schema document type and five fields: supplier name, document
  number, document date, currency, and total. Each field has evidence text and
  a stated confidence.
- Prompt registry key: `extraction-v2`.
- Known safety control: the v2 instructions explicitly reject commands embedded
  in a document, including commands that try to alter document classification.

### Policy assistant

- Models: `text-embedding-3-small` for query embeddings and `gpt-5-mini` for
  reranking and cited-answer synthesis; all are environment-configurable.
- Input: a user question plus a fixed allow-list of DocuGuard design-doc chunks.
- Output: a cited answer or `grounded: false` when the corpus does not support
  an answer.
- Prompt registry keys: recorded alongside calls in `llm_traces`; see
  `app/llmops/tracing.py`.

## Evaluation evidence

Extraction is measured separately from workflow behavior. The held-out CORD
report in `docs/eval-reports/cord-test-20260929T005242Z.json` records 95/95
correct totals and 100% accepted document-type accuracy. CORD does not provide
ground truth for supplier, document number, or currency in this mapping, so
those are enrichment flags rather than scored accuracy claims. A 100-sample
validation calibration run found 98.9% actual total accuracy in the dominant
0.9–1.0 stated-confidence bucket (92 of 98 samples); its smaller 0.7–0.9
bucket has only two samples and is not a reliable conclusion.

The extraction-injection evaluation in
`docs/eval-reports/extraction-robustness-20260929T150327Z.json` reports 4/4
resistant cases after the v2 prompt change. This is a small adversarial probe,
not a guarantee against all prompt-injection techniques.

For the policy assistant, the evaluation report in
`docs/eval-reports/policy-assistant-20260929T144047Z.json` records Recall@12
of 100% on its five authored in-corpus queries, citation support of 80%, and
100% on its three abstention and two injection-resistance probes. The corpus
and truth set are deliberately small; these are release-gate signals, not broad
benchmark claims.

## Operational monitoring

Every model call is traced with call type, model, prompt version, token counts,
latency, success/error outcome, and a best-effort redacted error message.
`GET /llmops/traces/summary` aggregates those traces by model/prompt-version
combination. Regex redaction covers common email, phone, SSN-like, and
card-like patterns, but does not reliably detect names or addresses.

## Important limitations

- Evaluation documents are receipts or synthetic examples, not representative
  of every vendor, language, layout, or enterprise invoice format.
- Confidence is model-reported and only partially calibrated for `total`; it is
  never an approval criterion.
- Native text extraction is not equivalent to robust OCR/layout understanding.
- Source evidence is currently text-span level. Page/bounding-box provenance
  remains a planned enhancement before claiming visual-document review parity.
- API model behavior can change over time. Prompt versions, evaluation reports,
  and trace grouping make such changes observable; they do not eliminate them.
