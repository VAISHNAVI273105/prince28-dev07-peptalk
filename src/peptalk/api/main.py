from fastapi import FastAPI

from peptalk.api.routes.documents import router as documents_router
from peptalk.api.routes.health import router as health_router
from peptalk.config import get_settings
from peptalk.logging_setup import setup_logging


def create_app() -> FastAPI:
    """Create and configure the PEPTalk FastAPI application."""

    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="PEPTalk",
        description="Python documentation assistant using official PEPs and What's New pages.",
        version="0.1.0",
    )

    app.include_router(health_router)
    app.include_router(documents_router)

    return app