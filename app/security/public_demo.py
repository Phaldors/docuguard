"""Guards that turn the app into a safe, fixed public portfolio demo.

The public deployment intentionally exposes only synthetic data.  These checks
live at the API boundary so the UI is not the thing enforcing the restriction.
"""

from hmac import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.demo.seed import DEMO_BUNDLE_ID


def is_public_demo() -> bool:
    return get_settings().public_demo


def restrict_to_demo_bundle(bundle_id: UUID) -> None:
    """Hide every non-demo bundle when portfolio-demo mode is enabled."""
    if is_public_demo() and bundle_id != DEMO_BUNDLE_ID:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        )


def block_public_demo_mutation() -> None:
    """Prevent visitors from creating data or starting processing jobs."""
    if is_public_demo():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This public demo is read-only.",
        )


def block_public_demo_protected_endpoint() -> None:
    """Avoid exposing spend-bearing or operational endpoints to the internet."""
    if is_public_demo():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in the public demo.",
        )


def require_demo_reviewer_access(
    x_docuguard_review_token: Annotated[str | None, Header()] = None,
) -> None:
    """Require an out-of-band code before a visitor can alter demo audit data."""
    settings = get_settings()
    if not settings.public_demo:
        return

    expected_token = settings.demo_review_token
    if expected_token is None or x_docuguard_review_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid reviewer access code is required.",
        )

    if not compare_digest(
        x_docuguard_review_token, expected_token.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid reviewer access code is required.",
        )
