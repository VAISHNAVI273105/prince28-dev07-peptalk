
import json
from pathlib import Path
from typing import Any


class DocumentStore:
    """Read and retrieve documentation records from a JSON file."""

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)

    def get_all(self) -> list[dict[str, Any]]:
        """Return all documentation records."""

        if not self.file_path.exists():
            return []

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Document data must be a JSON list")

        return data

    def get_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Return a document matching its ID."""

        for document in self.get_all():
            if document.get("id") == document_id:
                return document

        return None
