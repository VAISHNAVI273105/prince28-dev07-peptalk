# PEPTalk – Day 03 PostgreSQL Architecture & Implementation Notes

This document provides a comprehensive operational guide for the PostgreSQL database architecture, migrations, data loading, API endpoints, testing strategy, and index verification in the PEPTalk project.

---

## 1. Project Architecture

PEPTalk is a documentation assistant for modern Python versions (3.9 to 3.13) built with:

- **FastAPI**: Asynchronous web framework exposing REST endpoints (`/health`, `/ready`, `/v1/documents`).
- **SQLAlchemy 2.x**: Declarative Async ORM with `AsyncSession` and `async_sessionmaker`.
- **asyncpg**: Asynchronous PostgreSQL database driver for application connections.
- **psycopg (3.x)**: Synchronous PostgreSQL database driver dedicated to Alembic migration execution.
- **Neon PostgreSQL**: Cloud-hosted PostgreSQL instance in the AWS Asia Pacific Singapore region.
- **Alembic**: Database schema revision management supporting online and offline migrations.
- **Pydantic & Pydantic Settings**: Schema validation and settings management with `SecretStr` for credentials.

---

## D03 · PostgreSQL & Database Schema Summary

The database schema models Python documentation records and their associated text content.

### `documents` Table

Stores documentation sources, canonical hashes, and searchable JSONB metadata.

| Column | Type | Constraints / Default | Description |
|---|---|---|---|
| `id` | `VARCHAR` | Primary Key | Canonical document identifier (e.g. `pep-0634`, `whats-new-3-10`) |
| `title` | `VARCHAR` | `NOT NULL` | Human-readable document title |
| `source_url` | `TEXT` | `NOT NULL` | Canonical upstream URL |
| `licence` | `VARCHAR` | Nullable | Documentation license (optional) |
| `doc_type` | `VARCHAR` | `NOT NULL`, indexed | Document type (e.g. `PEP`, `What's New`) |
| `published_on` | `DATE` | Nullable, indexed | Publication date parsed from source record |
| `sha256` | `VARCHAR(64)` | `NOT NULL` | Deterministic SHA-256 hash computed from canonical JSON |
| `metadata` | `JSONB` | `NOT NULL`, default `{}` | Flexible metadata storing `status`, `python_version`, `pep_number`, etc. |

### Indices on `documents`

- `pk_documents`: Primary key on `id`.
- `ix_documents_doc_type`: B-Tree index on `doc_type` for type-based filtering.
- `ix_documents_published_on`: B-Tree index on `published_on` for chronological sorting/filtering.
- `ix_documents_metadata_gin`: PostgreSQL GIN index on `metadata` using the `jsonb_path_ops` operator class for JSONB containment (`@>`) queries.

### `pages` Table

Stores paginated text chunks associated with parent documents.

| Column | Type | Constraints / Default | Description |
|---|---|---|---|
| `doc_id` | `VARCHAR` | Composite PK, Foreign Key (`documents.id` ON DELETE CASCADE) | Parent document identifier |
| `page_no` | `INTEGER` | Composite PK, Check: `page_no > 0` | 1-indexed page sequence number |
| `text` | `TEXT` | `NOT NULL` | Document page content (e.g. summary or body chunk) |

### Constraints on `pages`

- Composite primary key on `(doc_id, page_no)`.
- Foreign key `fk_pages_doc_id_documents` referencing `documents.id` with cascading delete.
- Check constraint `ck_pages_page_no_positive`: `page_no > 0`.

---

## 3. Migration Revision History & Verification

Alembic manages schema versions using a linear revision chain.

### Revision Chain

1. **`ed7742f5a38a_create_documents_and_pages_tables.py`**
   - **Status**: Live-verified as applied on the Neon PostgreSQL database.
   - **Action**: Creates `documents` table, `pages` table, foreign keys, check constraints, and B-Tree indexes on `doc_type` and `published_on`.

2. **`c7a18f2d59b4_add_jsonb_gin_index_on_documents_metadata.py`**
   - **Status**: Live-verified as applied on the Neon PostgreSQL database and confirmed as the current head revision.
   - **Action**: Adds `ix_documents_metadata_gin` on `documents(metadata)` with `postgresql_using="gin"` and `postgresql_ops={"metadata": "jsonb_path_ops"}`.

### Migration Commands

```powershell
# View revision history
uv run alembic history --verbose

# View currently applied database revision
uv run alembic current

# Upgrade to latest revision (head)
uv run alembic upgrade head

# Roll back the most recent revision (downgrade)
uv run alembic downgrade -1
```

### Migration Verification Results

Neon PostgreSQL:
```text
c7a18f2d59b4 (head)
```

A separate local PostgreSQL test database was also used to verify:

- `uv run alembic upgrade head` — successful.
- `uv run alembic downgrade -1` — successful.
- `uv run alembic upgrade head` — successful again.

The local downgrade test did not modify the Neon production database.

---

## 4. Idempotent JSON-to-PostgreSQL Loader

The loader (`scripts/load_db.py`) imports documentation records from `data/sample_records.json` into PostgreSQL idempotently.

### Execution

```powershell
# Standard run using default data/sample_records.json
uv run python scripts/load_db.py

# Custom source file run
uv run python scripts/load_db.py --file data/sample_records.json
```

### Dataset Audit (22 Records)

`data/sample_records.json` contains 22 documentation records representing Python 3.10–3.13 features.

- All 22 records have unique string IDs.
- Records include PEP documentation and Python What's New documentation.
- Records contain source URLs, summaries, and metadata fields such as `status`, `python_version`, and `pep_number`.

### Field Mapping

- JSON `id` → `Document.id`
- JSON `title` → `Document.title`
- JSON `source_url` → `Document.source_url`
- JSON `type` → `Document.doc_type`
- JSON `created` → `Document.published_on` (parsed as `YYYY-MM-DD` date)
- JSON `summary` → `Page.text` with `Page.page_no = 1`
- Extra fields (`status`, `python_version`, `pep_number`, etc.) → `Document.document_metadata` (JSONB)

### Idempotency Guarantee

1. **Canonical JSON SHA-256**: Hashes are computed from key-sorted, compact JSON representations.
2. **Deterministic State Comparison**:
   - Record not in database → INSERT `Document` and `Page(page_no=1)`.
   - Record exists and `existing_doc.sha256 == new_sha256` → SKIP without modification.
   - Record exists and `existing_doc.sha256 != new_sha256` → UPDATE `Document` attributes and update `Page(page_no=1)` text in-place (no duplicate pages).
3. **Transactional Safety**: Operations are wrapped in an asynchronous transaction. Rollbacks occur automatically on failure.
4. **Credential Protection**: Secrets and connection strings are never printed in logs or terminal output.

### Actual Neon Loader Verification Outputs

**First run:**

```text
Loading complete from data\sample_records.json: 22 total (22 inserted, 0 updated, 0 skipped, 0 errors)
```

**Second run:**

```text
Loading complete from data\sample_records.json: 22 total (0 inserted, 0 updated, 22 skipped, 0 errors)
```

**Third run:**

```text
Loading complete from data\sample_records.json: 22 total (0 inserted, 0 updated, 22 skipped, 0 errors)
```

**Verification findings:**

- The first run inserted all 22 records.
- The second and third runs skipped all 22 unchanged records.
- No duplicate records were created.
- All three runs completed with zero errors.
- Idempotent loader behavior was successfully verified against Neon PostgreSQL.

---

## 5. API Endpoints, Filters & HTTP Error Behavior

### `GET /health` (Liveness Probe)

- **Status Code**: `200 OK`
- **Purpose**: Process liveness check, independent of database connectivity.
- **Response**:

```json
{
  "status": "healthy"
}
```

### `GET /ready` (Readiness Probe)

- **Status Code**: `200 OK` when database connectivity passes `SELECT 1`, or `503 Service Unavailable` when database connectivity fails.
- **Purpose**: Checks whether the application can access PostgreSQL.
- **Response**:

```json
{
  "status": "ready"
}
```

### `GET /v1/documents` (List Documents with Filters and Pagination)

**Query Parameters:**

- `limit` (int, 1–100, default: 20): Maximum records to return.
- `offset` (int, >= 0, default: 0): Starting record offset.
- `type` (string, optional): Filter by document type (e.g. `PEP`, `What's New`).
- `python_version` (string, optional): Filter by Python version format `X.Y` (e.g. `3.10`).
- `status` (string, optional): Filter by PEP status (e.g. `Final`, `Draft`, `Active`).
- `pep_number` (int, optional): Filter by positive integer PEP number (e.g. `634`).

**Validation:**

- Invalid filter inputs return `400 Bad Request` formatted according to RFC 9457 Problem Details (`application/problem+json`).
- Examples of invalid inputs: `python_version="invalid"`, `status="Unknown"`, `pep_number=-1`, `type="  "`.

### `GET /v1/documents/{document_id}` (Retrieve Single Document)

- **Status Code**: `200 OK` or `404 Not Found` (Problem Details).
- **Purpose**: Retrieves a single document including its summary from the `pages` table.

---

## 6. How to Run Tests

### Test Suite

Run the project test suite:

```powershell
uv run pytest
```

**Verified test result:**

```text
109 passed, 2 skipped
```

The two skipped tests are optional live database integration tests when a dedicated test database is not configured. The standard test suite does not require a live test database.

### Linting and Code Formatting Checks

```powershell
uv run ruff check .
uv run ruff format --check .
```

Both checks passed during project verification.

### Pre-commit Quality Verification

```powershell
uv run pre-commit run --all-files
```

### Optional Live Integration Tests

Live tests can be run against a dedicated test database:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://<user>:<password>@<test-host>:5432/test_db?ssl=require"

uv run pytest tests/test_integration_db.py

Remove-Item Env:\TEST_DATABASE_URL
```

> **Important:** Never configure `TEST_DATABASE_URL` with production database credentials. Use a separate test database.

---

## 7. GIN Index Details & EXPLAIN Query Analysis

PostgreSQL GIN indexes built with `jsonb_path_ops` support JSONB containment queries using the `@>` operator.

### Verification Script (`scripts/explain.py`)

Run the query planner analysis:

```powershell
uv run python scripts/explain.py
```

An optional Python version filter can also be supplied:

```powershell
uv run python scripts/explain.py --version 3.10
```

### Query Plan Analysis: Small Datasets vs Large Datasets

1. **Small-Table Cost Optimization**
   - For a small dataset of approximately 22 records, PostgreSQL can read the table with very little I/O.
   - A sequential scan may be more efficient than using a GIN index because index lookup has additional overhead.
   - PostgreSQL's cost-based query optimizer can therefore correctly choose a sequential scan for a small table.

2. **Forced Index Demonstration (`SET LOCAL enable_seqscan = off;`)**
   - When sequential scans are disabled for the demonstration, the planner can use a Bitmap Index Scan on `ix_documents_metadata_gin`.
   - `Bitmap Index Scan on ix_documents_metadata_gin`: Evaluates the JSONB containment condition and identifies matching heap locations.
   - `Bitmap Heap Scan on documents`: Uses the bitmap to retrieve matching table rows and rechecks the condition.

### Actual Neon EXPLAIN Output — 18 November 2026

**Query predicate:**

```sql
metadata @> '{"python_version": "3.10"}'::jsonb
```

**1. Default Query Plan**

```text
Seq Scan on documents
  Filter: (metadata @> '{"python_version": "3.10"}'::jsonb)
  Rows Removed by Filter: 16
  Actual rows: 6
  Execution Time: 0.060 ms
```

**2. Forced Index Query Plan**

```text
Bitmap Heap Scan on documents
  Recheck Cond: (metadata @> '{"python_version": "3.10"}'::jsonb)
  -> Bitmap Index Scan on ix_documents_metadata_gin
       Index Cond: (metadata @> '{"python_version": "3.10"}'::jsonb)
  Actual rows: 6
  Execution Time: 1.593 ms
```

### EXPLAIN Verification Findings

- The default PostgreSQL planner selected a sequential scan for the small 22-record dataset.
- The forced index plan successfully used `ix_documents_metadata_gin`.
- Both query plans returned 6 matching records.
- The default sequential scan execution time was `0.060 ms`.
- The forced index plan execution time was `1.593 ms`.
- The forced index scan was slower for this small dataset because of index lookup overhead.
- This does not indicate an index failure. It demonstrates that the GIN index exists and supports JSONB containment queries.
- Index performance should be evaluated again with a larger dataset before drawing performance conclusions.

---

## 8. Environment Variable Safety

- `.env` contains local development credentials and is excluded by `.gitignore`.
- `.env` must never be read, printed, exposed, staged, committed, or pushed.
- `.env.example` provides safe placeholder variables:

```text
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>
```

- All exception handlers and logging statements should sanitize database connection strings to prevent credential leakage.
- Never share database passwords, API keys, or complete connection strings in screenshots or GitHub commits.

---

## 9. Verification Status

The following Day 03 PostgreSQL implementation and verification tasks have been completed:

- Both Alembic migrations were successfully applied to Neon PostgreSQL.
- Local PostgreSQL testing verified `upgrade head`, `downgrade -1`, and `upgrade head` again.
- Current Neon migration revision: `c7a18f2d59b4` (head).
- The Neon database connection was successfully verified using `scripts/db_check.py`.
- Database connectivity was confirmed with a successful `SELECT 1`.
- The first Neon loader run inserted all 22 records.
- The second and third Neon loader runs skipped all 22 unchanged records.
- Idempotent loader behavior was verified with zero errors.
- GIN index `ix_documents_metadata_gin` was verified through actual EXPLAIN output.
- Default planner selected `Seq Scan` for the small dataset.
- Forced index verification demonstrated `Bitmap Index Scan` and `Bitmap Heap Scan`.
- Test suite: 109 passed, 2 skipped.
- Ruff lint check passed.
- Ruff format check passed.
- Day 03 PostgreSQL implementation and bug-fix changes were merged into `main` through GitHub pull requests.
---

## 10. Day 01 – Docker Image & Build Cache Verification

### Docker Image Build

- Image name: `peptalk:dev`
- Base image: `python:3.12-slim`
- Build tool: Docker BuildKit
- Dependency manager: UV `0.13.8`
- Initial full build time: 57.9 seconds
- Runtime-specific build time: 10.2 seconds
- Image content size: 162 MB
- Image disk usage: 647 MB

### Non-root User Verification

Command:

```powershell
docker run --rm peptalk:dev id
```

Actual output:

```text
uid=10001(app) gid=10001(app) groups=10001(app)
```

Result: Successfully verified that the runtime container runs as the dedicated non-root `app` user.

### Docker Build Cache Verification

A temporary docstring change was made in `src/peptalk/api/routes/health.py`, followed by a runtime image rebuild.

- Cache verification rebuild time: 18.8 seconds.
- Dependency installation layer (`uv sync --frozen --no-dev --no-install-project`): CACHED.
- Source code copy layer: Rebuilt.
- Final runtime image: Rebuilt.
- Original health-check docstring was restored after verification.

Result: Docker dependency-layer caching successfully verified.



**Final Note:** PostgreSQL migrations, Neon database connectivity, idempotent data loading, JSONB GIN index verification, and the project test suite have been successfully verified. Documentation evidence is recorded above.

---

## 11. Day 04 – Docker Compose, Multi-Stage Builds & Test Infrastructure Evidence

### Multi-Stage Dockerfile Verification

The multi-stage `Dockerfile` is structured into four distinct stages:
1. `builder`: Compiles dependencies using UV `0.13.8` with pinned Python 3.12-slim base image.
2. `runtime`: Minimal production runtime with non-root user `app` (UID 10001), virtual environment, and production entrypoint.
3. `test`: Includes development dependencies, test suites, and coverage reporting tools.
4. `final`: Final stage aliased as `FROM runtime AS final` to ensure default image builds target the production runtime.

Actual Image Measurements (`docker images peptalk:dev`):
- Content size: **74.6 MB**
- Disk usage: **318 MB**

Non-Root User Verification (`docker run --rm peptalk:dev id`):
```text
uid=10001(app) gid=10001(app) groups=10001(app)
```

Dependency Layer Caching Verification:
- First-build time with dependency download: ~54.1 seconds.
- Rebuild time with cached dependencies: **4.80 seconds**.
- Dependency layer (`uv sync --frozen --no-dev --no-install-project`): `CACHED`.

### Docker Compose Stack Verification

Docker Compose is defined in `docker-compose.yml` with four coordinated services:
- **db**: `pgvector/pgvector:pg17` with health check via `pg_isready -U peptalk -d peptalk` and initialization SQL mounted from `docker/initdb/01-create-test-db.sql`.
- **redis**: `redis:7-alpine` with health check via `redis-cli ping`.
- **migrate**: `peptalk:dev` running `alembic upgrade head && python scripts/load_db.py`, depending on `db: service_healthy`.
- **api**: `peptalk:dev` exposing port 8000, depending on `db: service_healthy`, `redis: service_healthy`, and `migrate: service_completed_successfully`.

Live Status (`docker compose ps -a`):
```text
NAME              IMAGE                    COMMAND                  SERVICE   STATUS                      PORTS
peptalk-api       peptalk:dev              "uvicorn peptalk.api…"   api       Up (healthy)                0.0.0.0:8000->8000/tcp
peptalk-db        pgvector/pgvector:pg17   "docker-entrypoint.s…"   db        Up (healthy)                5432/tcp
peptalk-migrate   peptalk:dev              "sh -c 'alembic upgr…"   migrate   Exited (0)
peptalk-redis     redis:7-alpine           "docker-entrypoint.s…"   redis     Up (healthy)                6379/tcp
```

Migration and Sample-Data Loading:
- Initial run: `20 total (20 inserted, 0 updated, 0 skipped, 0 errors)`.
- Subsequent run on restart (`docker compose down` followed by `docker compose up -d`): `20 total (0 inserted, 0 updated, 20 skipped, 0 errors)`.
- Idempotency verified: zero duplicate records created (20 unique records).

Live Endpoint Verification:
- `/health`: `200 OK` -> `{"status": "healthy"}`
- `/ready`: `200 OK` -> `{"status": "ready"}`
- `/docs`: `200 OK` (Swagger UI accessible)
- `/v1/documents`: `200 OK` (retrieves all 20 canonical documents)

Database Resilience Verification:
- Stopped database container (`docker compose stop db`):
  - `/health` remained healthy: `200 OK` (`{"status": "healthy"}`).
  - `/ready` reported failure: `503 Service Unavailable` (`{"status": 503, "detail": "Database connectivity check failed."}`).
- Restarted database container (`docker compose start db`):
  - `/ready` recovered: `200 OK` (`{"status": "ready"}`).

### Testing & Code Quality Verification

Test Suites:
- **Unit Tests** (`tests/unit/`): **109 passed** in 1.47s (95% statement coverage).
- **Integration Tests** (`tests/integration/`): **7 passed** in 0.82s against live PostgreSQL database (`peptalk_test`).
  1. `test_integration_database_migration_and_tables`
  2. `test_integration_repository_insert_and_get`
  3. `test_integration_repository_jsonb_filter`
  4. `test_integration_repository_pagination`
  5. `test_integration_loader_first_run` (verifies 20 inserted)
  6. `test_integration_loader_second_run_idempotent` (verifies 0 inserted, 20 skipped)
  7. `test_integration_api_readiness_probe`
- When `TEST_DATABASE_URL` is unset: all 7 integration tests skip safely.
- Combined Suite: **116 passed**, **92% total coverage**.

Poe the Poet Tasks:
- `test`, `test-unit`, `test-integration`, `test-cov`, `lint`, `format`, `check`, `up`, `down` configured in `pyproject.toml`.

Makefile:
- Formatted with genuine TAB indentation supporting `build`, `up`, `down`, `logs`, `test`, `test-unit`, `test-integration`, `lint`, `format`, `clean`.

Pre-commit Verification:
- All hooks passed: trailing whitespace, end of files, yaml check, ruff lint, ruff format, detect-secrets.

---

## 13. 30 Production-Grade Milestones Log (on `main`)

The codebase was elevated through exactly 30 distinct, verified, conventional git commits on `main`:

1. **M01 — Package metadata**: Added license, authors, keywords, classifiers, and project URLs to `pyproject.toml`.
2. **M02 — Dependency groups**: Adopted PEP 735 `dependency-groups` for test and lint tooling.
3. **M03 — Store typing & protocols**: Enhanced `DocumentStore` with PEP 695 type aliases and container protocols.
4. **M04 — Ruff lint rule sets**: Expanded lint coverage with `C4` (comprehensions), `PIE`, `RSE`, and `ISC`.
5. **M05 — OpenAPI schema metadata**: Enriched OpenAPI documentation with endpoint summaries, descriptions, and contact info.
6. **M06 — Pydantic response models**: Introduced typed `DocumentResponse` and `DocumentListResponse` schemas.
7. **M07 — Identifier and bounds validation**: Added validation rejecting empty identifiers and limiting `pep_number <= 99999`.
8. **M08 — RFC 9457 problem details factory**: Standardized error creation and added stack-trace error logging.
9. **M09 — Client IP diagnostic metadata**: Propagated sanitized `client_ip` to structured request JSON logs.
10. **M10 — Settings log level normalization**: Case-insensitive log levels, file extension checks, and environment helpers.
11. **M11 — Domain model repr**: Added informative `__repr__` and `__str__` to `Document` and `Page` models.
12. **M12 — Query efficiency**: Short-circuited document query on zero total count or out-of-bounds offset.
13. **M13 — Repository existence and count**: Added `exists()` and `count_documents()` to protocol, repository, and adapter.
14. **M14 — Migration metadata check**: Added `verify_migration_target_metadata()` guarding against missing tables.
15. **M15 — Connection pool recycling**: Added default `pool_recycle=1800` (30m) for serverless database resilience.
16. **M17 — PEP metadata validation**: Canonical PEP status normalization against standard PEP statuses.
17. **M17 — Ingestion error resilience**: Resilient record parsing continuing batch ingestion across malformed items.
18. **M18 — CPython version validation**: Format verification for minor release version strings (`^3\.\d+$`).
19. **M19 — In-memory deduplication**: Deduplication of identical records within single batch loading transactions.
20. **M20 — Repository search**: Case-insensitive search on titles and document identifiers in DB and memory.
21. **M21 — Resilient serialization**: Fallback summary extraction in `document_to_dict` serialization.
22. **M22 — Citation formatter**: Formatter producing markdown reference links for RAG and assistant responses.
23. **M23 — Python version validation**: Supported CPython release version validator (3.8-3.13).
24. **M24 — API edge-case tests**: Unit tests for blank ID (400), PEP bounds (400), pagination limits (422).
25. **M25 — Loader edge-case tests**: Unit tests for malformed JSON, missing summaries, database exception recovery.
26. **M26 — Integration test teardown**: Refined PostgreSQL connection termination in integration test cleanup.
27. **M27 — Reconnection recovery test**: Integration test verifying engine recovery after connection pool disposal.
28. **M28 — OCI container labels**: Added standard OCI container labels (`title`, `version`, `source`, `licenses`) in Dockerfile.
29. **M29 — Compose log rotation**: Configured container log rotation (`max-size: 10m`, `max-file: 3`) in `docker-compose.yml`.
30. **M30 — Developer documentation**: Documented complete 30-milestone engineering work and verification metrics.


---

## D05 · CI/CD and Going Live

- **Live URL**: https://peptalk-l60c.onrender.com
- **CI run for pull request 1**: https://github.com/VAISHNAVI273105/prince28-dev07-peptalk/actions/runs/44708952994
- **First deploy that ran by itself**: https://github.com/VAISHNAVI273105/prince28-dev07-peptalk/actions/runs/44711547991
- **Merge clicked at 15:20** → "Smoke test passed" at 15:39 → lead time: ~19 min

### Smoke test output from that CD run

```text
ok   /health -> 200, version bdef004820834519ac590146588dd2d72fc551a0
ok   /ready -> 200 {'status': 'ready'}
ok   /v1/documents?limit=1 -> 200
Smoke test passed
```

### Rollback drill

- Rolled back to sha `0adc04dcfe93fe164b4c656110dfda693387cb54` : started 15:42, smoke passed 15:44 (2 min)
- Rolled forward to sha `bdef004820834519ac590146588dd2d72fc551a0` : 2 min
- During the rollback, the database stayed on the newer schema. Why is that safe here?
  All database schema migrations follow strictly additive, backward-compatible patterns. The newer schema additions do not drop or break existing columns, so older application containers continue querying the existing fields without disruption.

### Where my secrets live

- Neon string: GitHub Secret `DATABASE_URL` + Render environment. Not in Git, not in the image.
- Render deploy hook: GitHub Secret `RENDER_DEPLOY_HOOK` only.

### Monitoring

- UptimeRobot checks `/health` every 5 minutes; alerts go to my email.
- One thing that would make my live app faster on its first request:
  The 5-minute external uptime ping prevents Render Free instances from entering idle sleep, and upgrading to a persistent tier eliminates cold-start spin-up latency entirely.

---

## D06 · Collecting the corpus

- Start target: Final + Active PEPs and What's New 3.10-3.13
- Collected today: 777 files, 5,138 pages, 17.0 MB (from DATASET.md)
- Doors used: URL list / Git repository

### Licence check

| Source | Licence or terms, in my words | May I show full text in answers? |
|---|---|---|
| peps | PEPs are public domain or CC0; Python docs PSF licence. | Yes, public domain/CC0 permits full quoting and answer presentation with attribution. |
| python-docs | PSF License (Python Software Foundation License version 2) | Yes, PSF license permits redistribution and excerpting with standard notice. |
| peps-web | Public domain or CC0 | Yes, full text can be quoted and shown in user answers. |

### robots.txt

- Site: docs.python.org & peps.python.org . Its robots.txt says (2 lines):
  docs.python.org disallows /dev/ and internal dynamic endpoints; /3.* documentation is permitted.
  peps.python.org disallows /build/ and internal artifacts; all published PEPs are permitted.
- Was anything blocked for my bot? What did I do about it?
  Nothing was blocked (0 blocked, 0 failed). The bot uses a polite 0.5s pause, max concurrency 4, and leverages Door 2 git shallow clone for batch PEP retrieval to avoid scraping burden.

### Kill and resume

- Run 1: I pressed Ctrl+C after 4 files
- Run 2: downloaded=6 skipped=4
- Run 3: downloaded=0 skipped=10

### Capacity (from docs/CAPACITY.md)

- Tokens per page, measured: 750
- Full corpus: 7.44 M tokens, 21,388 chunks, embedding about Rs 122, vectors 66 MB
- The number that surprised me most, and why (2 lines):
  Embedding 7.44M tokens (full 1,500 document corpus) costs only $1.28 (~Rs 122).
  I expected embeddings and storage to be substantial, but modern token pricing and pgvector footprint easily fit within free tier quotas.

### One thing that went wrong today, and how I fixed it
Door 2 (`scripts/fetch.py repo`) failed initially because `data/raw/peps` already existed from Door 1 HTML downloads. I separated the web-scraped PEP HTML sources into `peps-web` so `data/raw/peps` could cleanly host the shallow sparse Git checkout of `python/peps`.

### Crawl in numbers

- **Volume by source**: `peps` (767 files, 14.83 MB), `python-docs` (4 files, 1.63 MB), `peps-web` (6 files, 0.55 MB).
- **Slowest source**: `docs.python.org` (large 450+ KB single HTML docs), streamed cleanly with zero socket timeouts.
- **Reliability & duplicates**: 0 retries required, 0 blocked by robots.txt, 0 duplicates across 777 unique SHA256 hashes.
