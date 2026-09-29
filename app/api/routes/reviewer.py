from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.reviewer_ui import REVIEWER_PAGE

router = APIRouter(tags=["reviewer"])


@router.get("/reviewer", include_in_schema=False, response_class=HTMLResponse)
async def reviewer_page() -> str:
    """Serve the local human-review console without a separate frontend build."""
    return REVIEWER_PAGE
