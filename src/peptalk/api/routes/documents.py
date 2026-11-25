import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from peptalk.api.deps import get_document_repository
from peptalk.api.schemas import DocumentListResponse, DocumentResponse, PageResponse
from peptalk.db.repository import DocumentRepositoryProtocol

router = APIRouter(prefix="/v1/documents", tags=["documents"])

VALID_STATUSES = {
    "Draft",
    "Active",
    "Accepted",
    "Deferred",
    "Final",
    "Provisional",
    "Rejected",
    "Superseded",
    "Withdrawn",
}


def validate_filters(
    doc_type: str | None,
    python_version: str | None,
    status: str | None,
    pep_number: int | None,
) -> tuple[str | None, str | None, str | None, int | None]:
    """Validate query filter parameters, raising HTTP 400 for invalid inputs."""
    normalized_type = doc_type
    if doc_type is not None:
        stripped = doc_type.strip()
        if not stripped:
            raise HTTPException(status_code=400, detail="type filter cannot be empty.")
        normalized_type = stripped

    if python_version is not None and not re.match(r"^\d+\.\d+$", python_version.strip()):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid python_version filter '{python_version}'. "
                "Expected format 'X.Y' (e.g. '3.10')."
            ),
        )

    normalized_status = status
    if status is not None:
        formatted = status.strip().capitalize()
        if formatted not in VALID_STATUSES and status.strip() not in VALID_STATUSES:
            allowed = ", ".join(sorted(VALID_STATUSES))
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter '{status}'. Allowed statuses: {allowed}.",
            )
        normalized_status = formatted if formatted in VALID_STATUSES else status.strip()

    if pep_number is not None:
        if pep_number <= 0:
            raise HTTPException(
                status_code=400,
                detail="pep_number filter must be a positive integer greater than 0.",
            )
        if pep_number > 99999:
            raise HTTPException(
                status_code=400,
                detail="pep_number filter exceeds maximum allowable value (99999).",
            )

    return normalized_type, python_version, normalized_status, pep_number


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Python documentation records",
    description=(
        "Retrieve paginated Python PEP and What's New records with optional filtering "
        "by document type, Python language version, PEP status, and PEP number."
    ),
    response_description="A paginated list of matching Python documentation items.",
)
async def list_documents(
    repo: Annotated[DocumentRepositoryProtocol, Depends(get_document_repository)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: str | None = Query(default=None, description="Filter by document type (e.g. 'PEP')"),
    python_version: str | None = Query(
        default=None, description="Filter by Python version (e.g. '3.10')"
    ),
    status: str | None = Query(default=None, description="Filter by PEP status (e.g. 'Final')"),
    pep_number: int | None = Query(default=None, description="Filter by PEP number (e.g. 634)"),
) -> dict[str, Any]:
    norm_type, norm_version, norm_status, norm_pep = validate_filters(
        doc_type=type,
        python_version=python_version,
        status=status,
        pep_number=pep_number,
    )

    items, total = await repo.list_documents(
        limit=limit,
        offset=offset,
        doc_type=norm_type,
        python_version=norm_version,
        status=norm_status,
        pep_number=norm_pep,
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
    description=(
        "Retrieve complete metadata, publication date, source URL, and first-page text summary "
        "for a specific canonical Python document."
    ),
    response_description="Detailed document metadata and text content.",
)
async def get_document(
    document_id: str,
    repo: Annotated[DocumentRepositoryProtocol, Depends(get_document_repository)],
) -> dict[str, Any]:
    cleaned_id = document_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=400,
            detail="document_id cannot be blank or whitespace.",
        )
    document = await repo.get_by_id(cleaned_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{document_id}'.",
        )

    return document


@router.get(
    "/{document_id}/pages",
    response_model=PageResponse,
    summary="Get document page by page number",
    description="Retrieve the text content and heading hierarchy path of a specific document page.",
    response_description="Page content and section citation headings.",
)
async def get_document_page(
    document_id: str,
    repo: Annotated[DocumentRepositoryProtocol, Depends(get_document_repository)],
    page_no: int = Query(default=1, ge=1, description="1-indexed sequence page number."),
) -> dict[str, Any]:
    cleaned_id = document_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=400,
            detail="document_id cannot be blank or whitespace.",
        )

    if not await repo.exists(cleaned_id):
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{document_id}'.",
        )

    page = await repo.get_page(cleaned_id, page_no)
    if page is None:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_no} not found for document '{document_id}'.",
        )

    return page
