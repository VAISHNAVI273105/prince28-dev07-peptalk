from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from peptalk.api.deps import check_database_readiness

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe: verifies process health without database dependencies."""
    return {"status": "healthy"}


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
