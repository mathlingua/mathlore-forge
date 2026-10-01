"""FastAPI routes for serving static Mathlore rendered previews for pull requests."""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from mathlore_forge.preview.preview_manager import get_preview_file

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Previews"])


@router.get("/previews/{pr_number}")
async def redirect_preview_root(pr_number: int) -> Response:
    """Redirects to trailing slash so relative paths resolve cleanly."""
    return RedirectResponse(url=f"/previews/{pr_number}/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/previews/{pr_number}/{file_path:path}")
async def serve_preview_file(
    pr_number: int,
    file_path: str = "",
) -> Response:
    """Serves rendered Mathlore documentation files for a pull request."""
    data, content_type = await get_preview_file(pr_number=pr_number, file_path=file_path)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Preview file '{file_path}' for PR #{pr_number} not found. Please ensure the preview has been generated.",
        )

    # Set appropriate caching headers for preview assets vs HTML
    cache_control = "public, max-age=60" if content_type.startswith("text/html") else "public, max-age=86400"

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": cache_control,
            "X-Frame-Options": "ALLOWALL",
        },
    )
