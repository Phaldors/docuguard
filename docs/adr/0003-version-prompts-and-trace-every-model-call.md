# ADR 0003: Version prompts and trace every model call

- Status: accepted
- Date: 2026-09-29

## Context

Model behavior can shift after a provider/model/prompt change. Without a
correlation between a result, its prompt version, and runtime cost/latency,
regressions cannot be explained or compared.

## Decision

All four LLM call sites record call type, configured model, prompt version,
tokens, latency, outcome, and redacted error information in `llm_traces`.
Version constants live next to their prompts. Evaluation reports and the
regression-gate script are used before treating a prompt change as an
improvement.

## Consequences

This adds database writes and does not provide complete PII protection: current
redaction is regex-based and misses names/addresses. It does provide a concrete
operational record rather than relying on model configuration remembered by a
developer.
