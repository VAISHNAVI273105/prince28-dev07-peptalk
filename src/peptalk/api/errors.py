from fastapi import Request
from fastapi.responses import JSONResponse


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a 404 error using RFC 9457 Problem Details format."""

    return JSONResponse(
        status_code=404,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": str(exc),
            "instance": request.url.path,
        },
    )