from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

type DocumentRecord = dict[str, Any]


class DocumentStore:
    """Read and retrieve documentation records from a JSON file."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def __len__(self) -> int:
        """Return the count of documents currently available."""
        return len(self.get_all())

    def __iter__(self) -> Iterator[DocumentRecord]:
        """Iterate over all stored document records."""
        return iter(self.get_all())

    def get_all(self) -> list[DocumentRecord]:
        """Return all documentation records."""
        if not self.file_path.exists():
            return []

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Document data must be a JSON list")

        return data

    def get_by_id(self, document_id: str) -> DocumentRecord | None:
        """Return a document matching its ID."""
        for document in self.get_all():
            if document.get("id") == document_id:
                return document

        return None
