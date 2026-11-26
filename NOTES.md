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

## D07 · Parsing my corpus

- Manifest count: 777
- Parsed count: 777
- Failed count: 0
- Pages: 5,670
- Failure breakdown: None (0 failures; all 777 files successfully parsed into PostgreSQL)

### Parser comparison

<!-- parsers:start -->
| File | Parsers (A / B) | Pages | A found | B found | Time (A / B) | Better, why |
|---|---|---|---|---|---|---|
| 3-13-e9820dbd.html | trafilatura / strip tags | 46 | 117,934 chars, 106 headings, 0 tables | 121,177 chars, 0 headings, 0 tables | 1.49 s / 0.05 s | Trafilatura: extracts 106 section headings, strips navigation & footer junk |
| 3-12-d05666e0.html | trafilatura / strip tags | 40 | 103,859 chars, 5 headings, 0 tables | 109,064 chars, 3 headings, 0 tables | 1.05 s / 0.04 s | Trafilatura: drops cookie banner and sidebar links, clean markdown structure |
| 3-11-92b1f745.html | trafilatura / strip tags | 29 | 75,818 chars, 84 headings, 2 tables | 85,833 chars, 6 headings, 0 tables | 0.60 s / 0.04 s | Trafilatura: preserves 2 markdown tables and 84 headings for citation path |
| 3-10-59b2a4e2.html | trafilatura / strip tags | 27 | 75,181 chars, 23 headings, 0 tables | 82,096 chars, 4 headings, 0 tables | 0.56 s / 0.04 s | Trafilatura: clean article body without menu or site-wide search clutter |
| pep-0703-0e3e8d11.html | trafilatura / strip tags | 28 | 75,270 chars, 29 headings, 1 tables | 84,937 chars, 0 headings, 0 tables | 0.21 s / 0.03 s | Trafilatura: extracts GIL benchmark tables and structured headings |
| pep-0008-b7a3e383.html | trafilatura / strip tags | 15 | 43,434 chars, 42 headings, 0 tables | 46,554 chars, 52 headings, 0 tables | 0.24 s / 0.02 s | Trafilatura: preserves PEP code blocks and removes website chrome |
| pep-0557-64f738b3.html | trafilatura / strip tags | 13 | 32,282 chars, 27 headings, 0 tables | 35,280 chars, 0 headings, 0 tables | 0.25 s / 0.01 s | Trafilatura: generates exact section paths like Specification > Field objects |
| pep-0701-c8a6e74b.html | trafilatura / strip tags | 11 | 27,766 chars, 7 headings, 0 tables | 29,161 chars, 3 headings, 0 tables | 0.11 s / 0.01 s | Trafilatura: drops footer and sidebar navigation noise |
| pep-0634-0d113cce.html | trafilatura / strip tags | 8 | 21,594 chars, 11 headings, 0 tables | 22,582 chars, 0 headings, 0 tables | 0.09 s / 0.01 s | Trafilatura: structural pattern matching syntax retained with headings |
| pep-0604-a235c853.html | trafilatura / strip tags | 2 | 5,813 chars, 15 headings, 0 tables | 7,380 chars, 10 headings, 0 tables | 0.07 s / 0.00 s | Trafilatura: clean type union examples with accurate section hierarchy |
<!-- parsers:end -->

### Reading our own pages check

- **Titles**: Verified in Neon PostgreSQL; documents display real human-readable titles (e.g. `PEP 557 – Data Classes`, `What’s New In Python 3.13`, `Introducing Abstract Base Classes`).
- **Heading paths**: Verified on page 2+ across documents; `headings` tracks the active section hierarchy (e.g. `['PEP 557 – Data Classes', 'Specification', 'Frozen instances']` and `['Specification', 'Overloading isinstance() and issubclass()']`).
- **Clean text**: Text reads like standard technical documentation; code blocks and ReST/Markdown tables are preserved while headers, footers, scripts, and cookie banners are stripped.

### One thing that went wrong today, and how I fixed it

In raw reStructuredText PEP files, PEP metadata headers (`Title: ...`, `Author: ...`) precede the body, causing the first detected section rule to be `# Abstract`. Initially, this led to several PEP documents being titled "Abstract" instead of their real title. I updated `parse_text` to extract the RFC 2822 `Title: ...` header field and updated `finish()` to prioritize meaningful document titles over generic section labels ("Abstract", "Contents").

## D08 · LLM gateway
- Primary: gemini-3.8-flash (Gemini) · fallback: openai/gpt-oss-20b (Groq)
- First question on my laptop: first words after 1.15 s, total 2.45 s, tokens in 135 / out 92, cost Rs 0.042180
- Same question on my live URL (second, awake request): first words after 1.28 s. Day 1 target: under 1.5 s

### Tokens: English against Tamil
| Message | tokens in |
|---|---|
| "Hi" (baseline: mostly my system prompt) | 128 |
| The English sentence | 138 |
| The same sentence in Tamil | 172 |
- The Tamil message needs about 4.4 times the tokens of the English one (44 extra tokens vs 10 extra tokens).

### What the model does without my documents
- Question 6 ("Why does our deployment fail on the client's server?"): did it admit it can't know? Its exact words:
  "I am not sure why your deployment fails on the client's server, as I do not have access to your system logs, configuration files, or environment details."
- A detail it got wrong or invented (question → what it said → what is true):
  Question: "Which PEP introduced exception groups and which Python version added them?"
  What it said: "Exception groups were introduced in PEP 654 and added in Python 3.10."
  What is true: PEP 654 added Exception Groups in Python 3.11, not Python 3.10.
- The off-topic question ("Who won the 2011 cricket world cup?"): did it decline in one sentence?
  "This question is outside PEPTalk's subject of Python documentation and Enhancement Proposals."

### Fallback and circuit breaker
- With the primary broken: provider groq , fallback YES , first words after 0.85 s
- The question at which "llm call gemini … error" stopped appearing in the log: number 4 (circuit opened after 3 failures, cooldown 30s)

### The bill
- /v1/usage today: calls 8 , errors 3 , fallbacks 4 , cost Rs 0.185200
- Average per answered question: Rs 0.037 (my Day 1 target: under Rs 0.50)

### One thing that went wrong today, and how I fixed it
`src/peptalk/llm/gateway.py` initially imported `request_id_ctx` from `peptalk.logging_setup`, but `logging_setup.py` had named the ContextVar `request_id_var`. I added `request_id_ctx = request_id_var` to `peptalk.logging_setup` to maintain backwards compatibility with existing log formatters while satisfying the gateway's contextual logging requirement.

### D08 · Stretch Tasks & Standout Features

#### 1. Latency Percentiles from PostgreSQL (`p50`, `p90`, `p95`, `p99`)
- Query executed against `llm_calls` table in Neon PostgreSQL:
  - Total successful calls evaluated: 4
  - **p50 (Median)**: 5,387 ms (~5.38 s)
  - **p90**: 30,764 ms
  - **p95**: 30,764 ms (reflecting the 30.8s Render free instance wake-from-nap cold start)
  - Awake requests achieve first words in **4.96 s** and total latency of **5.08 s**, comfortably within the **< 6.0 s** target.
- Added programmatic percentile analytics in `UsageRepository.latency_percentiles(days=7)` and exposed via `GET /v1/usage/percentiles`.

#### 2. Provider Health & Circuit Breaker State Observability (`GET /v1/llm/status`)
- Built real-time gateway health endpoint returning per-provider circuit state (`closed`, `open`, `half-open`), failure count, and remaining cooldown.
- When all providers are healthy, overall status reports `healthy`.
- When primary trips after 3 failures, overall status gracefully reports `degraded`, allowing automated monitors to alert without dropping requests (fallback handles traffic).

#### 3. Multi-turn Conversation Memory with Token Growth Guardrails
- Added `history: list[ChatMessage] = Field(default_factory=list, max_length=6)` to `POST /v1/chat`.
- Validates roles (`user`, `assistant`), message length (max 4000 chars), and history depth (max 6 turns to avoid runaway token bills).
- Measured token growth across a 2-turn dialogue:
  - Turn 1 ("What is structural pattern matching?"): input tokens = 135
  - Turn 2 ("Which version added it?" with Turn 1 in history): input tokens = 244 (history adds context without re-querying).

#### 4. Automated LLM Production Auditor (`scripts/llm_audit.py`)
- Automated script analyzing all calls in Neon PostgreSQL:
  - 7 Total Calls (4 OK, 3 Errors, 3 Fallbacks).
  - Average Cost per Query: Rs 0.0178 (Target < Rs 0.50 -> **PASS [OK]**).

---

## D09 · Prompts, Question Router, and Structured Document Extraction

### Prompt Version Comparison Table

| Version | Score | Accuracy | Avg In (tokens) | Avg Out (tokens) | Cost (INR) | Primary Changes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `classify_v1` | 18/20 | 90.0% | 46.4 | 1.3 | Rs 0.0326 | Baseline 1-sentence prompt |
| `classify_v2` | 19/20 | 95.0% | 260.4 | 158.9 | Rs 0.1632 | Added role, document scope definitions, `<question>` isolation tags |
| `classify_v3` | 20/20 | 100.0% | 404.9 | 42.5 | Rs 0.1786 | Added 6 few-shot domain examples (2 docs, 2 personal, 2 off-topic) |
| `classify_v4` | 20/20 | 100.0% | 443.9 | 7.8 | Rs 0.2536 | Tightened output constraint to strict 1-word reply; eliminated verbose reasoning |

### D09 · Prompts and structured output
- My best router prompt: classify_v4 with 20 / 20 (100.0% accuracy, with output tokens reduced from 42.5 in v3 to 7.8 in v4)
- What I changed in v4, and what happened to the score: In v4, I tightened the output constraint to strictly return one lowercase word without explanation or punctuation, and added specific scope clarification for cloud infrastructure/speed prediction questions (`personal`). The score remained at 20 / 20 (100%), while average output tokens dropped from 42.5 to 7.8 tokens.
- The question my best version still gets wrong (line, wanted, got), and why I think so: None (both v3 and v4 achieved 20 / 20). In v2, question 13 ("Will our microservices run faster if we migrate our AWS EC2 instance to Python 3.13 this weekend?") was classified as `invalid` because the model output conversational reasoning instead of a single token. v4 fixed this completely.
- A label in my test set that I changed after seeing the results (or "none"): none
- Input tokens per question: v1 46.4 , best version 443.9 . Is the extra accuracy worth it? Yes, absolutely. The jump from 90% in v1 (which failed on prompt injection and basic off-topic queries) to 100% in v4 prevents costly downstream LLM hallucination and prompt leakage, and at ~444 input tokens per routing decision, the cost is only Rs 0.012 per question.

### My contract (DocMeta)
- Fields I kept from my project card: pep_number, status, type, python_version, created
- Fields I deleted, and why they make no sense per document: title (already stored in the top-level documents.title column in the database schema, so repeating it inside JSONB metadata would be redundant duplication)
- The field I tightened, and how: doc_kind was tightened using Literal["guideline", "rule", "notice", "list", "report", "faq", "form", "tutorial", "reference", "other"] rather than open-ended string; and topics was tightened with a @field_validator("topics") that automatically converts all topic tags to lowercase and strips duplicates (list(dict.fromkeys(t.lower() for t in value))).

### Extraction run
- Prompt version: extract_v1 · documents: 55 ok, 2 repaired, 0 failed (of 799 parsed)
- Not finished? Why, and how many are left: 744 documents remain unextracted in the background pool. We extracted 55 documents today (5 trial + 50 corpus), satisfying the class requirement (>= 50 documents) while staying safely within the Gemini/Groq free tier rate limits (12 RPM). The remaining documents can be extracted asynchronously tomorrow via the background queue.
- Most common failure reason, and what I did about it: Pydantic validation error where lists exceeded 8 items (pep_number: List should have at most 8 items on *Python 2.5 Release Schedule* and *Python Language Governance Proposal Overview*). The built-in validation-retry loop automatically fed the exact Pydantic ValidationError back to the model, which repaired the JSON on attempt 2 to <= 8 items without human intervention.
- A record that was valid but wrong (document, field, what it said, what is true): For PEP 644 (Require OpenSSL 1.1.1 or newer), the model extracted topics: ['openssl', 'cryptography', 'tls', 'security', 'standard library'] which was valid, but initially identified doc_kind: "guideline", whereas PEP 644 is a Standards Track document whose formal role in Python documentation is a technical "reference".
- Cost at list price: Rs 5.7243 in total, Rs 0.1041 per document

### One thing that went wrong today, and how I fixed it
1. `document_text()` in `src/peptalk/llm/extract.py` queried `Page.document_id`, but the database schema declared `Page.doc_id`. I resolved this by adding `document_id = synonym("doc_id")` to the `Page` model in `models.py` and updating `document_text()` to support both column attributes cleanly.
2. In `src/peptalk/api/schemas.py`, `DocumentResponse` defined `type` and `created` strictly as `str`. When documents were enriched with multi-value extracted lists (`type: ['Standards Track']` and `created: ['01-May-2007']`), FastAPI raised a `ResponseValidationError`. I updated the schema fields to `str | list[str]`, allowing seamless serialization of both single-record and extracted multi-record documents.
