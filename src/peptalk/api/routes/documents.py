from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from peptalk.api.deps import get_document_store
from peptalk.store import DocumentStore

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.get("")
async def list_documents(
    store: Annotated[DocumentStore, Depends(get_document_store)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    documents = store.get_all()

    return {
        "total": len(documents),
        "limit": limit,
        "offset": offset,
        "items": documents[offset : offset + limit],
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    store: Annotated[DocumentStore, Depends(get_document_store)],
) -> dict[str, Any]:
    document = store.get_by_id(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document with id '{document_id}'.",
        )

    return document
