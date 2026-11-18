# PEPTalk – Day 03 PostgreSQL Architecture & Implementation Notes

This document provides a comprehensive operational guide for the PostgreSQL database architecture, migrations, data loading, API endpoints, testing strategy, and index verification in the PEPTalk project.

---

## 1. Database Schema Summary

The database uses PostgreSQL with SQLAlchemy 2.x asynchronous ORM models and Alembic migrations.

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

## 2. Migration Commands

Alembic manages database schema versions. Synchronous driver `psycopg` is automatically utilized during migration runs.

### View Migration History
```powershell
uv run alembic history --verbose
```

### View Current Migration State
```powershell
uv run alembic current
```

### Apply All Pending Migrations (Upgrade to Head)
```powershell
uv run alembic upgrade head
```

### Roll Back One Revision (Downgrade)
```powershell
uv run alembic downgrade -1
```

### Migration History Chain
1. `ed7742f5a38a_create_documents_and_pages_tables.py`: Initial schema creation for `documents` and `pages`.
2. `c7a18f2d59b4_add_jsonb_gin_index_on_documents_metadata.py`: Adds `ix_documents_metadata_gin` on `documents(metadata)` with `jsonb_path_ops`.

---

## 3. Idempotent JSON-to-PostgreSQL Loader

The loader imports documentation records from `data/sample_records.json` into PostgreSQL idempotently.

### Execution
Run via `uv`:
```powershell
uv run python scripts/load_db.py
```

Or specify a custom file:
```powershell
uv run python scripts/load_db.py --file data/sample_records.json
```

### Idempotency Guarantee
1. **Canonical JSON SHA-256**: Hashes are computed from key-sorted, compact JSON representations.
2. **Deterministic State Comparison**:
   - If the record does not exist in the database $\rightarrow$ **INSERT** `Document` and `Page(page_no=1)`.
   - If the record exists and `existing_doc.sha256 == new_sha256` $\rightarrow$ **SKIP** without modification.
   - If the record exists and `existing_doc.sha256 != new_sha256` $\rightarrow$ **UPDATE** `Document` attributes and update `Page(page_no=1)` text in-place (no duplicate pages).
3. **Transactional Safety**: All record operations are executed within an asynchronous transaction. Rollbacks occur automatically on failure.
4. **Credential Protection**: Secrets and database connection strings are never printed in logs or terminal output.

---

## 4. API Endpoints and Filters

### `GET /health` (Liveness Probe)
- **Status Code**: `200 OK`
- **Purpose**: Process liveness check, decoupled from database connectivity.
- **Response**:
  ```json
  {"status": "healthy"}
  ```

### `GET /ready` (Readiness Probe)
- **Status Code**: `200 OK` (when database responds to `SELECT 1`) or `503 Service Unavailable` (when database connectivity fails).
- **Response**:
  ```json
  {"status": "ready"}
  ```

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

## 5. How to Run Tests

### Unit Tests (Offline, Fast, No Live Database Required)
Unit tests run completely isolated using mocks and repository adapters:
```powershell
uv run pytest
```

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
$env:TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@test-host:5432/test_db?ssl=require"
uv run pytest tests/test_integration_db.py
Remove-Item Env:\TEST_DATABASE_URL
```
> [!IMPORTANT]
> Never configure `TEST_DATABASE_URL` with production database credentials.

---

## 6. How to Verify GIN Index Using EXPLAIN

In PostgreSQL, GIN indexes built with `jsonb_path_ops` accelerate containment queries using the `@>` operator.

### SQL Verification Query
Execute in `psql` or database query console:
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, metadata
FROM documents
WHERE metadata @> '{"status": "Final", "python_version": "3.10"}'::jsonb;
```

### Expected Query Plan
When the table contains representative volume and statistics are analyzed (`ANALYZE documents;`), PostgreSQL produces a plan utilizing the GIN index:

```text
Bitmap Heap Scan on documents  (cost=12.05..24.50 rows=5 width=248) (actual time=0.042..0.055 rows=5 loops=1)
  Recheck Cond: (metadata @> '{"status": "Final", "python_version": "3.10"}'::jsonb)
  Buffers: shared hit=4
  ->  Bitmap Index Scan on ix_documents_metadata_gin  (cost=0.00..12.05 rows=5 width=0) (actual time=0.028..0.028 rows=5 loops=1)
        Index Cond: (metadata @> '{"status": "Final", "python_version": "3.10"}'::jsonb)
        Buffers: shared hit=2
Planning Time: 0.120 ms
Execution Time: 0.082 ms
```

### Plan Interpretation
- **`Bitmap Index Scan on ix_documents_metadata_gin`**: PostgreSQL probes the GIN index using the path and value hashes for `status: Final` and `python_version: 3.10`.
- **`Bitmap Heap Scan on documents`**: Fetches matching rows from table pages using the bitmap created by the index scan.
- **`jsonb_path_ops` Advantage**: Produces a significantly smaller index size and faster lookup compared to default `jsonb_ops` for containment predicates.
