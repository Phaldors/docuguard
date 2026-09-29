# ADR 0001: Human review owns final case decisions

- Status: accepted
- Date: 2026-09-28

## Context

Document extraction is probabilistic and reconciliation detects only the rules
that have been implemented. An incorrect approval can cause operational or
financial harm, while an unnecessary review costs only reviewer time.

## Decision

Every reconciled bundle transitions to `ready_for_review`. Only a human may
transition it to `approved`, `rejected`, or `needs_info`, and every decision
requires an actor and reason. Corrections and decisions create append-only
`AuditEvent` records; original model extraction is not overwritten.

## Consequences

This sacrifices automation rate in v1 and prevents a fully touchless workflow.
In return, the system has a clear accountability boundary, a reconstructible
case history, and no confidence threshold that can silently approve a case.
