# PEPTalk

**Your Modern Python Documentation Assistant**

PEPTalk is a Python documentation assistant project designed to help developers explore Python Enhancement Proposals (PEPs), Python release notes, and version-specific language changes through structured, authoritative documentation.

It focuses on making Python documentation easier to navigate, especially when developers need to understand when a feature was introduced and which Python versions support it.

---

## Project Status

**Day 04 – Docker & Test Infrastructure**

The project currently includes:

- FastAPI application with an application factory.
- Dependency injection and structured JSON logging.
- Document storage using PostgreSQL and SQLAlchemy.
- Database migrations managed with Alembic.
- Health and readiness endpoints.
- Dockerized API and database infrastructure.
- Isolated PostgreSQL test database.
- Automated unit and integration tests.

## Who It's For

- **Python Developers:** Exploring new Python features and version changes.
- **Library Authors:** Understanding compatibility across Python versions.
- **Engineering Teams:** Researching documentation during Python upgrades.
- **Students and Learners:** Finding reliable references for Python concepts.

## Problem Statement

Python documentation is distributed across PEPs, release notes, and official documentation pages. Finding the correct source and identifying the Python version in which a feature was introduced can take time.

PEPTalk aims to simplify this process by organizing authoritative Python documentation into a structured and searchable system.

## Key Project Goals

- Organize official Python documentation.
- Associate documentation with relevant Python versions.
- Provide document retrieval through REST API endpoints.
- Maintain reliable database storage and migrations.
- Build a foundation for version-aware documentation assistance.

## Official Data Sources

PEPTalk references official Python resources:

- [Python Documentation](https://docs.python.org/3/)
- [Python Enhancement Proposals](https://peps.python.org/)
- [What's New in Python](https://docs.python.org/3/whatsnew/)

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.12+ |
| Package Manager | uv |
| API Framework | FastAPI |
| ASGI Server | Uvicorn |
| Validation | Pydantic |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Testing | Pytest |
| Coverage | pytest-cov |
| Linting | Ruff |
| Containers | Docker |
| Orchestration | Docker Compose |
| Supporting Service | Redis |

## Project Structure

```text
PEPTalk/
├── .dockerignore
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── README.md
│
├── data/
│   └── sample_records.json
│
├── docs/
│   ├── QUESTIONS.md
│   └── REQUIREMENTS.md
│
├── migrations/
│   ├── env.py
│   └── versions/
│
├── scripts/
│   ├── db_check.py
│   ├── explain.py
│   └── load_db.py
│
├── src/
│   └── peptalk/
│       ├── config.py
│       ├── logging_setup.py
│       ├── main.py
│       ├── store.py
│       ├── api/
│       │   ├── deps.py
│       │   ├── errors.py
│       │   ├── main.py
│       │   ├── middleware.py
│       │   └── routes/
│       │       ├── documents.py
│       │       └── health.py
│       └── db/
│           ├── base.py
│           ├── models.py
│           ├── repository.py
│           └── session.py
│
└── tests/
    ├── conftest.py
    ├── unit/
    └── integration/
```

## Getting Started

### Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop (for containerized setup)

### 1. Clone the Repository

```bash
git clone https://github.com/VAISHNAVI273105/prince28-dev07-peptalk.git
cd prince28-dev07-peptalk
```

### 2. Install Dependencies

```bash
uv sync --dev
```

### 3. Configure Environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required local environment values in `.env` if needed. Never commit your `.env` file or expose credentials.

### 4. Run Locally

```bash
uv run uvicorn peptalk.api.main:create_app --factory --reload
```

The API will be available at:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/ready

## Run locally in one command

Start the entire PEPTalk stack (PostgreSQL with pgvector, Redis, migrations, sample data loading, and FastAPI application) in the background with a single command:

```bash
docker compose up --build -d
```

The stack automatically:
1. Boots `pgvector/pgvector:pg17` and initializes databases (`peptalk` and `peptalk_test`).
2. Boots `redis:7-alpine`.
3. Runs the `migrate` service (`peptalk:dev`) to apply Alembic migrations and idempotently load 20 sample records into PostgreSQL.
4. Boots the `api` service (`peptalk:dev`) as non-root user `app` (UID 10001) once database migrations complete and services are healthy.

Access the running application:
- Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Liveness Probe: [http://localhost:8000/health](http://localhost:8000/health)
- Readiness Probe: [http://localhost:8000/ready](http://localhost:8000/ready)
- Documents Collection: [http://localhost:8000/v1/documents](http://localhost:8000/v1/documents)

To stop the services:
```bash
docker compose down
```

## Run with Docker

Start the API, PostgreSQL, and Redis services:

```bash
docker compose up --build
```

Stop the services:

```bash
docker compose down
```

## Run Tests

### Local Tests

```bash
uv run pytest --cov=peptalk --cov-report=term-missing
```

### Docker Test Runner

Run the isolated test database and test runner:

```bash
docker compose --profile test run --build --rm test-runner
```

The test profile uses a separate PostgreSQL test database so integration tests do not run against the application's normal database.

### Latest Verified Test Results

| Metric | Result |
|---|---:|
| Tests passed | 134 unit tests (plus 8 live integration tests) |
| Code coverage | 96% |
| Docker image size | 74.6 MB content size (318 MB disk usage, <400 MB requirement) |
| Container security | Non-root app user (uid=10001) |

These are results from the latest recorded Docker test and image checks; they may change as the project evolves.

## 30 Development Milestones

The project was evolved through 30 production-grade development milestones on `main`:

| No. | Milestone | Description |
|---|---|---|
| M01 | Package metadata | Complete PyPI classifiers, author, keywords, and repository URLs |
| M02 | Dependency groups | PEP 735 organized `test` and `lint` dependency groups |
| M03 | Store typing & protocols | PEP 695 type aliases, container protocols (`__len__`, `__iter__`) |
| M04 | Ruff lint expansion | Enforce `C4`, `PIE`, `RSE`, and `ISC` comprehensive rule sets |
| M05 | OpenAPI schema docs | Rich endpoint summaries, operation IDs, tags, contact metadata |
| M06 | Pydantic response models | Typed `DocumentResponse` and `DocumentListResponse` schemas |
| M07 | Parameter edge-case validation | Identifier whitespace and PEP number bounds checks (<=99999) |
| M08 | RFC 9457 error factory | Standardized problem details factory with exception trace logging |
| M09 | Client IP diagnostics | Sanitized client IP extraction in structured JSON request logs |
| M10 | Settings validation | Log level case normalization and `.is_production`/`.is_testing` helpers |
| M11 | Domain model repr | Informative `__repr__` and `__str__` methods for Document and Page |
| M12 | Query efficiency | Short-circuit document query on zero total count or out-of-bounds offset |
| M13 | Repository existence & count | Dedicated `exists()` and `count_documents()` repository methods |
| M14 | Migration metadata safety | Startup metadata integrity check verifying registered model tables |
| M15 | Connection pool reliability | Automatic connection recycling (`pool_recycle=1800`) for async engine |
| M16 | PEP metadata validation | Canonical PEP status normalization against standard statuses |
| M17 | Ingestion error resilience | Resilient parsing skipping malformed records without failing batch |
| M18 | CPython version validation | Validation for CPython release version strings (`^3\.\d+$`) |
| M19 | In-memory deduplication | In-memory deduplication of identical records during batch ingestion |
| M20 | Repository search | Case-insensitive keyword search on document titles and identifiers |
| M21 | Resilient serialization | Safe fallback summary extraction in `document_to_dict` |
| M22 | Citation formatting | Assistant citation formatter generating markdown reference links |
| M23 | Python version accuracy | Supported CPython version validation helper (3.8-3.13) |
| M24 | API edge-case tests | Unit tests for blank ID (400), PEP bounds (400), pagination limits (422) |
| M25 | Loader edge-case tests | Unit tests for malformed JSON, missing summaries, database error handling |
| M26 | Integration test teardown | Robust PostgreSQL process termination and cleanup in test fixtures |
| M27 | Reconnection recovery test | Live integration test verifying engine recovery after connection drop |
| M28 | OCI container labels | Standard OCI labels (title, version, source, license) in Dockerfile |
| M29 | Compose log rotation | Standardized container log rotation limits (`max-size: 10m`, `max-file: 3`) |
| M30 | Milestone documentation | Comprehensive developer documentation and verification report |

## Code Quality Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pre-commit run --all-files
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check |
| GET | `/v1/documents` | Retrieve documents |
| GET | `/v1/documents/{document_id}` | Retrieve a specific document |

## Project Information

- **Program:** Prince 2028 – GenAI Engineer Program
- **Project ID:** DEV-07
- **Project Name:** PEPTalk
- **Repository:** [GitHub – PEPTalk](https://github.com/VAISHNAVI273105/prince28-dev07-peptalk)

---

*Built as part of the Prince 2028 GenAI Engineer Program.*
