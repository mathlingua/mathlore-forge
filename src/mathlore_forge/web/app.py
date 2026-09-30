"""FastAPI application factory for Mathlore Forge."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from mathlore_forge.config import ensure_env_loaded
from mathlore_forge.storage.db import init_db
from mathlore_forge.web.routes.api import router as api_router
from mathlore_forge.web.routes.dashboard import router as dashboard_router
from mathlore_forge.web.routes.webhooks import router as webhooks_router

ensure_env_loaded()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for database initialization."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///mathlore_forge.sqlite")
    init_db(db_url)
    yield


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title="Mathlore Forge",
        description="Autonomous, Durable, Self-Improving AI Forge System for Mathlore",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Health check for GCP Cloud Run
    @app.get("/healthz", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "mathlore-forge"}

    # Favicon handler to prevent 404 noise
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    # Register routers
    app.include_router(dashboard_router)
    app.include_router(webhooks_router)
    app.include_router(api_router)

    return app


app = create_app()
