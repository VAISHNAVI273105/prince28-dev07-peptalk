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

## 2. Database Schema Summary

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

**Final Note:** PostgreSQL migrations, Neon database connectivity, idempotent data loading, JSONB GIN index verification, and the project test suite have been successfully verified. Documentation evidence is recorded above.