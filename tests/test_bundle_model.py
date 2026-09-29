import pytest
from sqlalchemy import select

from app.db.session import session_factory
from app.models.bundle import DocumentBundle


@pytest.mark.asyncio
async def test_new_bundle_gets_database_defaults() -> None:
    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="test-tenant")

        session.add(bundle)
        await session.flush()
        await session.refresh(bundle)

        stored_bundle = await session.scalar(
            select(DocumentBundle).where(DocumentBundle.id == bundle.id)
        )

        assert stored_bundle is not None
        assert stored_bundle.tenant_id == "test-tenant"
        assert stored_bundle.status == "received"
        assert stored_bundle.created_at is not None
