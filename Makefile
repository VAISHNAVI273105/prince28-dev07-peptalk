.PHONY: help build up down logs test test-unit test-integration lint format clean

help:
	@echo "PEPTalk development targets:"
	@echo "  build            Build Docker development image"
	@echo "  up               Start Docker Compose services in background"
	@echo "  down             Stop and remove Docker Compose containers"
	@echo "  logs             Follow Docker Compose logs"
	@echo "  test             Run full test suite"
	@echo "  test-unit        Run unit test suite"
	@echo "  test-integration Run integration test suite"
	@echo "  lint             Run linter checks"
	@echo "  format           Format codebase"
	@echo "  clean            Clean build and cache artifacts"

build:
	docker build -t peptalk:dev .

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

test-integration:
	uv run pytest tests/integration

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]; [shutil.rmtree(p) for p in [pathlib.Path('.pytest_cache'), pathlib.Path('.ruff_cache'), pathlib.Path('htmlcov')] if p.exists()]; pathlib.Path('.coverage').unlink(missing_ok=True)"
