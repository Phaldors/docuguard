"""Create the versioned synthetic reviewer demo in the configured database."""

import argparse
import asyncio

from app.db.session import engine, session_factory
from app.demo.seed import seed_demo


async def main(*, replace: bool) -> None:
    async with session_factory() as session:
        bundle = await seed_demo(session, replace=replace)
        await session.commit()

    print("DocuGuard reviewer demo is ready.")
    print(f"Bundle ID: {bundle.id}")
    print("Expected findings: one critical total mismatch and one advisory low confidence.")
    print("Queue: http://127.0.0.1:8000/bundles?status=ready_for_review")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace only the fixed DocuGuard demo bundle with a clean copy.",
    )
    args = parser.parse_args()
    asyncio.run(main(replace=args.reset))
