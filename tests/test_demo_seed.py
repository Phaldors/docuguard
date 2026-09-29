import pytest
from sqlalchemy import select

from app.db.session import session_factory
from app.demo.seed import DEMO_BUNDLE_ID, DEMO_DOCUMENTS, seed_demo
from app.models.discrepancy import BundleDiscrepancy
from app.models.document import Document
from app.reconciliation.rules import DiscrepancyType, Severity


@pytest.mark.asyncio
async def test_demo_seed_creates_a_repeatable_review_case() -> None:
    async with session_factory() as session:
        bundle = await seed_demo(session, replace=True)
        await session.commit()

        documents = list(
            await session.scalars(
                select(Document)
                .where(Document.bundle_id == DEMO_BUNDLE_ID)
                .order_by(Document.original_filename)
            )
        )
        discrepancies = list(
            await session.scalars(
                select(BundleDiscrepancy)
                .where(BundleDiscrepancy.bundle_id == DEMO_BUNDLE_ID)
                .order_by(BundleDiscrepancy.discrepancy_type)
            )
        )

    assert bundle.status == "ready_for_review"
    assert len(documents) == len(DEMO_DOCUMENTS)
    assert {(item.discrepancy_type, item.severity) for item in discrepancies} == {
        (DiscrepancyType.LOW_CONFIDENCE_FIELD.value, Severity.ADVISORY.value),
        (DiscrepancyType.TOTAL_MISMATCH.value, Severity.CRITICAL.value),
    }


@pytest.mark.asyncio
async def test_demo_seed_is_idempotent_without_reset() -> None:
    async with session_factory() as session:
        first = await seed_demo(session, replace=True)
        await session.commit()
        second = await seed_demo(session)

    assert first.id == second.id == DEMO_BUNDLE_ID
