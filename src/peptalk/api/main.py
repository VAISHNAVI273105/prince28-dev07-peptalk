from fastapi import FastAPI

from peptalk.api.errors import register_exception_handlers
from peptalk.api.middleware import RequestContextMiddleware
from peptalk.api.routes.documents import router as documents_router
from peptalk.api.routes.health import router as health_router
from peptalk.config import get_settings
from peptalk.logging_setup import setup_logging


def create_app() -> FastAPI:
    """Create and configure the PEPTalk FastAPI application."""

    settings = get_settings()
    setup_logging(settings.log_level)

    openapi_tags = [
        {
            "name": "health",
            "description": "Liveness and readiness probes for infrastructure monitoring.",
        },
        {
            "name": "documents",
            "description": (
                "Operations for querying, filtering, and retrieving Python PEP and release records."
            ),
        },
    ]

    app = FastAPI(
        title="PEPTalk",
        description="Python documentation assistant using official PEPs and What's New pages.",
        version="0.1.0",
        openapi_tags=openapi_tags,
        contact={
            "name": "PEPTalk Engineering Team",
            "url": "https://github.com/VAISHNAVI273105/prince28-dev07-peptalk",
        },
        license_info={
            "name": "MIT",
        },
    )

    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(documents_router)

    return app
