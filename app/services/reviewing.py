"""Reviewer actions: per-field corrections and bundle-level case decisions.

Per docs/reviewer-workflow.md, DocuGuard never edits the original extraction.
A correction or a decision is only ever appended as an AuditEvent; the
DocumentFieldExtraction row a reviewer is looking at stays exactly as the
model produced it.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.bundle import DocumentBundle
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction

CORRECTABLE_FIELDS = {
    "document_type",
    "supplier_name",
    "document_number",
    "document_date",
    "currency",
    "total",
}
CORRECTION_ACTIONS = {"kept", "corrected", "marked_unavailable"}
DECISION_ACTIONS = {"approved", "rejected", "needs_info"}


class BundleNotFoundError(Exception):
    """Raised when a bundle cannot be found."""


class DocumentNotFoundError(Exception):
    """Raised when a document cannot be found in the given bundle."""


class UnknownFieldError(Exception):
    """Raised when a correction targets a field DocuGuard does not track."""


class InvalidActionError(Exception):
    """Raised when an action/value/reason combination is invalid."""


class InvalidBundleStateError(Exception):
    """Raised when a case decision is made from a state that does not allow it."""


async def record_field_correction(
    *,
    session: AsyncSession,
    bundle_id: UUID,
    document_id: UUID,
    field_name: str,
    action: str,
    actor: str,
    new_value: str | None = None,
    reason: str | None = None,
) -> AuditEvent:
    if field_name not in CORRECTABLE_FIELDS:
        raise UnknownFieldError(f"'{field_name}' is not a tracked field.")
    if action not in CORRECTION_ACTIONS:
        raise InvalidActionError(f"Unknown correction action '{action}'.")
    if action == "corrected" and not new_value:
        raise InvalidActionError(
            "A corrected value is required when action is 'corrected'."
        )
    if action in {"corrected", "marked_unavailable"} and not reason:
        raise InvalidActionError(f"A reason is required when action is '{action}'.")

    document = await session.scalar(
        select(Document).where(
            Document.id == document_id, Document.bundle_id == bundle_id
        )
    )
    if document is None:
        raise DocumentNotFoundError

    field_extraction = await session.scalar(
        select(DocumentFieldExtraction).where(
            DocumentFieldExtraction.document_id == document_id
        )
    )
    prior_value = None
    if field_extraction is not None:
        prior_value = (
            field_extraction.document_type
            if field_name == "document_type"
            else getattr(field_extraction, f"{field_name}_value")
        )

    event = AuditEvent(
        bundle_id=bundle_id,
        document_id=document_id,
        event_type="field_correction",
        action=action,
        field_name=field_name,
        prior_value=prior_value,
        new_value=new_value if action == "corrected" else None,
        actor=actor,
        reason=reason,
    )
    session.add(event)
    await session.flush()
    return event


async def record_case_decision(
    *,
    session: AsyncSession,
    bundle_id: UUID,
    action: str,
    actor: str,
    reason: str,
) -> tuple[DocumentBundle, AuditEvent]:
    if action not in DECISION_ACTIONS:
        raise InvalidActionError(f"Unknown decision action '{action}'.")
    if not reason:
        raise InvalidActionError("A reason is required for every case decision.")

    bundle = await session.get(DocumentBundle, bundle_id)
    if bundle is None:
        raise BundleNotFoundError
    if bundle.status != "ready_for_review":
        raise InvalidBundleStateError(
            f"Bundle is '{bundle.status}', not 'ready_for_review'; "
            "it cannot be decided."
        )

    event = AuditEvent(
        bundle_id=bundle_id,
        document_id=None,
        event_type="case_decision",
        action=action,
        field_name=None,
        prior_value=bundle.status,
        new_value=action,
        actor=actor,
        reason=reason,
    )
    session.add(event)
    bundle.status = action

    await session.flush()
    return bundle, event
