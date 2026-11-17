
import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("peptalk.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and processing time to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"

            logger.info(
                "Request completed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed_ms, 2),
                },
            )

            return response

        except Exception:
            logger.exception("Unhandled request error")
            raise

        finally:
            request_id_var.reset(token)
