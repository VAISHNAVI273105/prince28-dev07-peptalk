from typing import Any

from fastapi import Depends, FastAPI

from peptalk.config import Settings, get_settings

app = FastAPI(
    title="PEPTalk",
    description="An AI-powered Python documentation assistant",
    version="0.1.0",
)


@app.get("/")
async def home():
    return {
        "message": "Welcome to PEPTalk!",
        "status": "running",
    }


@app.get("/health")
async def health_check(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return {
        "status": "healthy",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": settings.git_sha,
    }
