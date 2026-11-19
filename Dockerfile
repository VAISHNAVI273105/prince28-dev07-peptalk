# ---------- Stage 1: Builder ----------
FROM python:3.12-slim AS builder

# Install the pinned UV version
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Install production dependencies first
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Install the PEPTalk application
COPY src ./src
RUN uv sync --frozen --no-dev


# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

# Create a dedicated non-root application user
RUN useradd --create-home --uid 10001 app

WORKDIR /app

# Copy the prepared virtual environment
COPY --from=builder --chown=app:app /opt/venv /opt/venv

# Copy application resources
COPY --chown=app:app src ./src
COPY --chown=app:app data ./data
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

# Runtime configuration
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    DATA_FILE=/app/data/sample_records.json

# Run as a non-root user
USER app

EXPOSE 8000

# API liveness check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# Start FastAPI
CMD ["uvicorn", "peptalk.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
