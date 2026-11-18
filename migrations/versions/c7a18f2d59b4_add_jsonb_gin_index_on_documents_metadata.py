"""add jsonb gin index on documents metadata

Revision ID: c7a18f2d59b4
Revises: ed7742f5a38a
Create Date: 2026-11-18 13:08:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a18f2d59b4"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "ed7742f5a38a"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add GIN index on documents metadata column."""
    op.create_index(
        "ix_documents_metadata_gin",
        "documents",
        ["metadata"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"metadata": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Downgrade schema: drop GIN index on documents metadata column."""
    op.drop_index(
        "ix_documents_metadata_gin",
        table_name="documents",
        postgresql_using="gin",
    )
