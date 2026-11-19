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
| Tests passed | 111 |
| Code coverage | 95% |
| Docker image size | Approximately 71 MB |

These are results from the latest recorded Docker test and image checks; they may change as the project evolves.

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
