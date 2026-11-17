# PEPTalk

**Your Modern Python Documentation Assistant**

PEPTalk is an authoritative Python documentation assistant that helps developers navigate Python version changes, newly introduced features, and language specifications using official Python Enhancement Proposals (PEPs) and Python "What's New" guides.

---

## Project Status

**Day 1 Foundation – Complete (Active Development)**

Core infrastructure, FastAPI application factory, dependency injection, JSON structured logging, RFC 9457 error contracts, pre-commit quality hooks, and documentation datasets are implemented and verified.

---

## Who It's For

- **Python Developers & Engineering Teams**: Engineers upgrading legacy codebases from Python 3.9 through Python 3.13 who need fast, definitive answers on syntax changes, deprecated modules, and standard library replacements.
- **Library Authors & Maintainers**: Developers managing cross-version compatibility matrices who need precise version boundaries for typing enhancements, runtime behaviors, and bytecode changes.
- **Architects & Tech Leads**: Teams evaluating migration risks, performance trade-offs (such as free-threaded CPython and JIT compilation), and upgrade timelines.

---

## Problem Statement

When upgrading across multiple Python minor versions (such as Python 3.9 to 3.13), developers encounter documentation scattered across dozens of PEPs, release notes, changelogs, and bug tracker threads. General-purpose LLMs frequently hallucinate PEP numbers, confuse release version boundaries (e.g., conflating PEP 604 union syntax with PEP 695 type parameter syntax), and provide inaccurate code examples. PEPTalk solves this by delivering deterministic, version-grounded answers anchored directly in canonical Python documentation.

---

## Signature Feature: Python Version Gate

The **Python Version Gate** is PEPTalk's signature mechanism for cross-version compatibility:
- **Version Boundaries**: Validates whether a feature, syntax construct, or library function is available in a target Python runtime (3.10, 3.11, 3.12, 3.13).
- **Migration Guidance**: When querying an unsupported or newly introduced feature, the gate identifies the exact introduction version, migration alternatives, and official deprecation notices.
- **Canonical Attribution**: Every response links directly to the normative PEP or official "What's New in Python" document.

---

## Hardest Problem & Engineering Story

**Resolving Specification Disambiguation Across Evolving PEPs**

A significant challenge in Python documentation engineering is disambiguating multi-part proposals and overlapping language changes across consecutive minor versions. For example:
- Pattern matching spans four documents (PEPs 622, 634, 635, and 636), but only PEP 634 serves as the normative specification for Python 3.10.
- Multithreading changes evolve from per-interpreter GIL (PEP 684 in Python 3.12) to optional free-threading (PEP 703 in Python 3.13).

To eliminate ambiguity, PEPTalk implements a decoupled architecture with:
1. **Deterministic Document Store**: An indexed, typed repository with strict schemas for PEP status, release versions, and source URLs.
2. **FastAPI Dependency Injection**: Decoupled store providers ensuring test isolation, swappable backends, and zero global mutable state.
3. **Strict RFC 9457 Error Handling**: Standardized Problem Details responses for validation errors, missing documents, and runtime exceptions.
4. **Structured JSON Observability**: Request-correlated logging with millisecond duration tracking to debug and monitor every request end-to-end.

---

## Target Metrics

| Metric | Target | Current Status |
|---|---|---|
| **Hallucination Rate** | 0% (zero fabricated PEPs or URLs) | 0% (grounded in official sources) |
| **P95 Latency** | < 200 ms for document queries | < 15 ms local retrieval |
| **Test Coverage** | 100% passing automated test suite | 21 passing tests |
| **Error Contract** | 100% RFC 9457 Problem Details | Fully compliant |
| **Code Quality** | Zero lint, format, or typing errors | Clean Ruff & pre-commit checks |

---

## Data Sources

PEPTalk references exclusively official, authoritative Python documentation:
- **Python Documentation**: https://docs.python.org/3/
- **Official PEP Repository**: https://peps.python.org/
- **What's New in Python**: https://docs.python.org/3/whatsnew/

---

## Tech Stack

- **Runtime**: Python 3.12+ (managed with `uv`)
- **API Framework**: FastAPI 0.115+
- **Server**: Uvicorn (ASGI)
- **Settings & Validation**: Pydantic Settings v2
- **Testing**: Pytest 9.2+ & HTTPX TestClient
- **Code Quality**: Ruff (linter & formatter)
- **Git Hooks**: pre-commit (pre-commit-hooks, ruff, detect-secrets)

---

## Project Structure

```text
PEPTalk/
├── .env.example              # Environment template
├── .gitignore                # Git ignore patterns
├── .pre-commit-config.yaml   # Pre-commit hook configuration
├── pyproject.toml            # Project metadata & tool configuration
├── README.md                 # Project documentation
├── uv.lock                   # Deterministic dependency lockfile
├── data/
│   └── sample_records.json   # 22 official Python PEP & What's New records
├── docs/
│   ├── QUESTIONS.md          # 10 core evaluation questions
│   └── REQUIREMENTS.md       # Functional & non-functional requirements
├── src/
│   └── peptalk/
│       ├── config.py         # Type-safe settings with Pydantic
│       ├── logging_setup.py  # Structured JSON log formatter
│       ├── store.py          # Document store reader
│       └── api/
│           ├── deps.py       # FastAPI dependency providers
│           ├── errors.py     # RFC 9457 error handlers
│           ├── main.py       # FastAPI application factory
│           ├── middleware.py # Request ID & timing middleware
│           └── routes/
│               ├── documents.py # Document listing & retrieval
│               └── health.py    # Health & readiness checks
└── tests/
    ├── conftest.py           # Shared test fixtures & client setup
    ├── test_api.py           # API integration tests
    └── test_config.py        # Configuration & dependency injection tests
```

---

## Local Setup & Run Instructions

### 1. Prerequisites
- Python 3.12 or newer
- [`uv`](https://github.com/astral-sh/uv) package manager

### 2. Install Dependencies
```bash
uv sync
```

### 3. Environment Configuration
Copy the template to `.env` if not already present:
```bash
cp .env.example .env
```

Allowed environment settings:
- `APP_ENV`: `local`, `ci`, or `production`
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`
- `DATA_FILE`: Path to documentation JSON file (defaults to `data/sample_records.json`)

### 4. Run the Application
Start the development server with hot reload:
```bash
uv run uvicorn peptalk.api.main:create_app --factory --reload --no-access-log
```

Interactive API documentation will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Quality Checks

Run all verification tools locally:

```bash
# Run test suite
uv run pytest

# Check formatting and linting
uv run ruff check .
uv run ruff format --check .

# Run pre-commit hooks across all files
uv run pre-commit run --all-files
```

---

## Project Info

- **Program**: Prince 2028 - GenAI Engineer Program
- **Project**: DEV-07 | PEPTalk
