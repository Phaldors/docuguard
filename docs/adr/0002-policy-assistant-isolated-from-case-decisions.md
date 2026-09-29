# ADR 0002: Isolate the policy assistant from case decisions

- Status: accepted
- Date: 2026-09-29

## Context

A conversational interface is useful for explaining DocuGuard's workflow, but
letting it read arbitrary bundle documents or influence a reviewer decision
would expand its access and prompt-injection surface.

## Decision

The policy assistant retrieves only from an explicit allow-list of DocuGuard
design documents. It produces cited answers about workflow/policy, not a
bundle-specific recommendation. Retrieval, reranking, and answer synthesis are
separate from extraction and reconciliation services.

## Consequences

The assistant cannot answer every operational question and may abstain when
the fixed corpus is insufficient. In exchange, its data boundary is auditable,
the corpus is versioned, and it cannot become an implicit approval channel.
