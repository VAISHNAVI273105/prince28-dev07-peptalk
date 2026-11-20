import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def create_problem_details(
    status_code: int,
    detail: str,
    instance: str,
    title: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Construct an RFC 9457 compliant Problem Details dictionary."""
    resolved_title = title or ("Not Found" if status_code == 404 else "HTTP Error")
    payload: dict[str, Any] = {
        "type": "about:blank",
        "title": resolved_title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    payload.update(extra)
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    """Register RFC 9457 Problem Details exception handlers."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            media_type="application/problem+json",
            content=create_problem_details(
                status_code=exc.status_code,
                detail=str(exc.detail),
                instance=request.url.path,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content=create_problem_details(
                status_code=422,
                title="Unprocessable Content",
                detail="Request validation failed.",
                instance=request.url.path,
                errors=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled application exception processing %s: %s", request.url.path, exc
        )
        return JSONResponse(
            status_code=500,
            media_type="application/problem+json",
            content=create_problem_details(
                status_code=500,
                title="Internal Server Error",
                detail="An unexpected error occurred.",
                instance=request.url.path,
            ),
        )
