from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parents[1] / ".env.test",
    override=True,
)

import pytest_asyncio
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine

settings = get_settings()

if not settings.database_url.endswith("/docuguard_test"):
    raise RuntimeError("Tests must use the dedicated DocuGuard test database.")


@pytest_asyncio.fixture(autouse=True)
async def reset_database_after_test() -> AsyncIterator[None]:
    yield

    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE audit_events, bundle_discrepancies, "
                "document_field_extractions, document_extractions, "
                "document_processing_jobs, documents, document_bundles"
            ),
        )

    await engine.dispose()
