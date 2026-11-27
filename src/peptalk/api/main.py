import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from peptalk.api.errors import register_exception_handlers
from peptalk.api.middleware import RequestContextMiddleware
from peptalk.api.routes.chat import load_prompt
from peptalk.api.routes.chat import router as chat_router
from peptalk.api.routes.documents import router as documents_router
from peptalk.api.routes.health import router as health_router
from peptalk.api.routes.ingest import router as ingest_router
from peptalk.config import get_settings
from peptalk.db.llm_calls import record_call
from peptalk.llm.gateway import build_gateway
from peptalk.logging_setup import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    worker_task = None
    if settings.worker_in_api:
        from arq.worker import create_worker

        from peptalk.workers.main import WorkerSettings

        worker = create_worker(WorkerSettings)
        worker_task = asyncio.create_task(worker.async_run())

    yield

    if worker_task:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
    queue = getattr(app.state, "queue", None)
    if queue and hasattr(queue, "pool"):
        await queue.pool.close()


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
        {
            "name": "chat",
            "description": "Streaming LLM chat completion and token usage metrics.",
        },
        {
            "name": "ingest",
            "description": "Background document ingestion, status tracking, and dead-letter queue.",
        },
    ]

    app = FastAPI(
        title="PEPTalk",
        description="Python documentation assistant using official PEPs and What's New pages.",
        version="0.1.0",
        openapi_tags=openapi_tags,
        lifespan=lifespan,
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

    # Attach LLM prompt and gateway to app state
    app.state.settings = settings
    app.state.system_prompt = load_prompt(settings.prompts_dir)
    try:
        from peptalk.llm.prompts import load_prompt as load_task_prompt

        app.state.router_prompt, app.state.router_version = load_task_prompt(
            "classify", prompts_dir=settings.prompts_dir
        )
    except Exception:
        app.state.router_prompt, app.state.router_version = "", ""
    app.state.gateway = build_gateway(settings, recorder=record_call)

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(chat_router, prefix="/v1")
    app.include_router(ingest_router, prefix="/v1")

    return app
