from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from peptalk.api.deps import check_database_readiness
from peptalk.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Liveness probe: verifies process health and returns version metadata."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": settings.git_sha,
    }


@router.get("/ready")
async def readiness_check(
    is_ready: Annotated[bool, Depends(check_database_readiness)],
) -> dict[str, str]:
    """Readiness probe: verifies database connectivity."""
    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail="Database connectivity check failed.",
        )
    return {"status": "ready"}
