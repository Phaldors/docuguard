import asyncio

from app.db.session import session_factory
from app.storage.dependencies import get_document_storage
from app.workers.document_processor import process_next_document


async def main() -> None:
    async with session_factory() as session:
        did_process = await process_next_document(
            session=session,
            storage=get_document_storage(),
        )

    print("Processed one document job." if did_process else "No queued document jobs.")


if __name__ == "__main__":
    asyncio.run(main())
