# PEPTalk – Day 03 PostgreSQL Architecture & Implementation Notes

This document provides a comprehensive operational guide for the PostgreSQL database architecture, migrations, data loading, API endpoints, testing strategy, and index verification in the PEPTalk project.

---

## 1. Project Architecture

PEPTalk is a documentation assistant for modern Python versions (3.9 to 3.13) built with:
- **FastAPI**: Asynchronous web framework exposing REST endpoints (`/health`, `/ready`, `/v1/documents`).
- **SQLAlchemy 2.x**: Declarative Async ORM with `AsyncSession` and `async_sessionmaker`.
- **asyncpg**: High-performance asynchronous PostgreSQL database driver for application connections.
- **psycopg (3.x)**: Synchronous PostgreSQL database driver dedicated to Alembic migration execution.
- **Neon PostgreSQL**: Cloud-hosted PostgreSQL instance in the **US-East (Ohio, `us-east-2`)** region.
- **Alembic**: Database schema revision management supporting online and offline migrations.
- **Pydantic & Pydantic-Settings**: Schema validation and settings management with `SecretStr` for credentials.

---

## 2. Database Schema Summary

The database schema models Python documentation records and their associated text content.

### `documents` Table
Stores documentation sources, canonical hashes, and searchable JSONB metadata.

| Column | Type | Constraints / Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR` | Primary Key | Canonical document identifier (e.g. `pep-0634`, `whats-new-3-10`) |
| `title` | `VARCHAR` | `NOT NULL` | Human-readable document title |
| `source_url` | `TEXT` | `NOT NULL` | Canonical upstream URL |
| `licence` | `VARCHAR` | `NULLABLE` | Documentation license (optional) |
| `doc_type` | `VARCHAR` | `NOT NULL`, Index: `ix_documents_doc_type` | Document type (e.g. `PEP`, `What's New`) |
| `published_on` | `DATE` | `NULLABLE`, Index: `ix_documents_published_on` | Publication date parsed from source record |
| `sha256` | `VARCHAR(64)` | `NOT NULL` | Deterministic SHA-256 hash computed from canonical JSON |
| `metadata` | `JSONB` | `NOT NULL`, Default: `'{}'::jsonb`, GIN Index: `ix_documents_metadata_gin` | Flexible metadata storing `status`, `python_version`, `pep_number`, etc. |

#### Indices on `documents`
- `pk_documents`: Primary key on `id`.
- `ix_documents_doc_type`: B-Tree index on `doc_type` for type-based filtering.
- `ix_documents_published_on`: B-Tree index on `published_on` for chronological sorting/filtering.
- `ix_documents_metadata_gin`: PostgreSQL GIN index on `metadata` using the `jsonb_path_ops` operator class for high-performance JSONB containment (`@>`) queries.

### `pages` Table
Stores paginated text chunks associated with parent documents.

| Column | Type | Constraints / Default | Description |
| :--- | :--- | :--- | :--- |
| `doc_id` | `VARCHAR` | Composite PK, Foreign Key (`documents.id` `ON DELETE CASCADE`) | Parent document identifier |
| `page_no` | `INTEGER` | Composite PK, Check: `page_no > 0` | 1-indexed page sequence number |
| `text` | `TEXT` | `NOT NULL` | Document page content (e.g. summary or body chunk) |

#### Constraints on `pages`
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
   - **Status**: Head revision in codebase; ready to be applied.
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
`data/sample_records.json` contains 22 verified documentation records representing Python 3.10–3.13 features:
- All 22 records have unique string IDs (`pep-0634` through `pep-0667`, plus 4 `whats-new-3-XX` records).
- All records have valid official source URLs (`https://peps.python.org/` or `https://docs.python.org/`).
- All records have non-empty summaries and valid metadata fields (`status`, `python_version`, `pep_number`).

### Field Mapping
- JSON `id` $\rightarrow$ `Document.id`
- JSON `title` $\rightarrow$ `Document.title`
- JSON `source_url` $\rightarrow$ `Document.source_url`
- JSON `type` $\rightarrow$ `Document.doc_type`
- JSON `created` $\rightarrow$ `Document.published_on` (parsed as `YYYY-MM-DD` date)
- JSON `summary` $\rightarrow$ `Page.text` with `Page.page_no = 1`
- Extra fields (`status`, `python_version`, `pep_number`, etc.) $\rightarrow$ `Document.document_metadata` (JSONB)

### Idempotency Guarantee
1. **Canonical JSON SHA-256**: Hashes are computed from key-sorted, compact JSON representations.
2. **Deterministic State Comparison**:
   - Record not in database $\rightarrow$ **INSERT** `Document` and `Page(page_no=1)`.
   - Record exists and `existing_doc.sha256 == new_sha256` $\rightarrow$ **SKIP** without modification.
   - Record exists and `existing_doc.sha256 != new_sha256` $\rightarrow$ **UPDATE** `Document` attributes and update `Page(page_no=1)` text in-place (no duplicate pages).
3. **Transactional Safety**: All operations are wrapped in an asynchronous transaction. Rollbacks occur automatically on failure.
4. **Credential Protection**: Secrets and connection strings are never printed in logs or terminal output.

---

## 5. API Endpoints, Filters & HTTP Error Behavior

### `GET /health` (Liveness Probe)
- **Status Code**: `200 OK`
- **Purpose**: Process liveness check, completely independent of database connectivity.
- **Response**: `{"status": "healthy"}`

### `GET /ready` (Readiness Probe)
- **Status Code**: `200 OK` (when database connectivity passes `SELECT 1`) or `503 Service Unavailable` (when database connectivity fails).
- **Response**: `{"status": "ready"}`

### `GET /v1/documents` (List Documents with Filters and Pagination)
- **Query Parameters**:
  - `limit` (int, 1–100, default: 20): Maximum records to return.
  - `offset` (int, $\ge 0$, default: 0): Starting record offset.
  - `type` (string, optional): Filter by document type (e.g. `PEP`, `What's New`).
  - `python_version` (string, optional): Filter by Python version format `X.Y` (e.g. `3.10`).
  - `status` (string, optional): Filter by PEP status (e.g. `Final`, `Draft`, `Active`).
  - `pep_number` (int, optional): Filter by positive integer PEP number (e.g. `634`).
- **Validation**:
  - Invalid filter inputs return `400 Bad Request` formatted according to RFC 9457 Problem Details (`application/problem+json`).
  - Examples of invalid inputs: `python_version="invalid"`, `status="Unknown"`, `pep_number=-1`, `type="  "`.
- **Response**:
  ```json
  {
    "total": 1,
    "limit": 20,
    "offset": 0,
    "items": [
      {
        "id": "pep-0634",
        "title": "Structural Pattern Matching: Specification",
        "type": "PEP",
        "source_url": "https://peps.python.org/pep-0634/",
        "created": "2020-09-12",
        "licence": null,
        "pep_number": 634,
        "status": "Final",
        "python_version": "3.10",
        "summary": "Specifies the syntax and semantics of the match statement..."
      }
    ]
  }
  ```

### `GET /v1/documents/{document_id}` (Retrieve Single Document)
- **Status Code**: `200 OK` or `404 Not Found` (Problem Details).
- **Response**: Single document object including summary from `pages` table.

---

## 6. How to Run Tests

### Unit Tests (Offline, Fast, No Live Database Required)
Unit tests run completely isolated using mocks and repository adapters:
```powershell
uv run pytest
```
*Current test result: 109 passed, 2 skipped (100% offline).*

### Linting and Code Formatting Checks
```powershell
uv run ruff check .
uv run ruff format --check .
```

### Pre-commit Quality Verification
```powershell
uv run pre-commit run --all-files
```

### Optional Live Integration Tests
Live tests are skipped by default. To run against a dedicated test database:
```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://<user>:<password>@<test-host>:5432/test_db?ssl=require"
uv run pytest tests/test_integration_db.py
Remove-Item Env:\TEST_DATABASE_URL
```
> [!IMPORTANT]
> Never configure `TEST_DATABASE_URL` with production database credentials.

---

## 7. GIN Index Details & EXPLAIN Query Analysis

PostgreSQL GIN indexes built with `jsonb_path_ops` accelerate containment queries using the `@>` operator.

### Verification Script (`scripts/explain.py`)
Run the query planner analysis:
```powershell
uv run python scripts/explain.py --version 3.10
```

### Query Plan Analysis: Small Datasets vs Large Datasets
1. **Small-Table Cost Optimization**:
   - For a small dataset (e.g. 20–22 rows), the entire table resides in a single 8KB disk page. A sequential scan reads exactly 1 buffer page with an estimated startup cost of `0.00` and total cost around `1.0 - 1.3`.
   - A GIN index lookup requires reading GIN index pages, building an in-memory bitmap, and then performing a bitmap heap scan, which carries an estimated startup cost of `8.0 - 12.0`.
   - PostgreSQL's cost-based query optimizer correctly chooses a sequential scan as the fastest and most efficient access path for small tables.
2. **Forced Index Demonstration (`SET LOCAL enable_seqscan = off;`)**:
   - When sequential scans are disabled, or as the dataset grows to thousands of documentation records, the planner switches to a **Bitmap Index Scan** on `ix_documents_metadata_gin`.
   - **`Bitmap Index Scan on ix_documents_metadata_gin`**: Evaluates `metadata @> '{"python_version": "3.10"}'::jsonb` using path and value hashes, producing a bitmask of matching heap blocks.
   - **`Bitmap Heap Scan on documents`**: Reads heap blocks in physical order using the bitmask and evaluates the recheck condition.

---

## 8. Environment Variable Safety

- `.env` contains local development credentials and is excluded by `.gitignore`.
- `.env` must never be read, printed, exposed, staged, committed, or pushed.
- `.env.example` provides safe placeholder variables (`DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>/<database>`).
- All exception handlers and logging statements sanitize database connection strings to prevent credential leakage.

---

## 9. Remaining Limitations

- Migration `c7a18f2d59b4` (GIN index) is defined in code and verified with unit tests; applying it to live Neon PostgreSQL requires user authorization.
- Loader execution on live Neon PostgreSQL is implemented, tested with mocks, and awaits user confirmation.
