
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from peptalk.api.middleware import RequestContextMiddleware
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

    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=404,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
                "detail": exc.detail,
                "instance": request.url.path,
            },
        )

    app.include_router(health_router)
    app.include_router(documents_router)

    return app
