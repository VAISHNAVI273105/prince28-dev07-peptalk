
from fastapi import FastAPI

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
async def health_check():
    return {
        "status": "healthy",
    }
