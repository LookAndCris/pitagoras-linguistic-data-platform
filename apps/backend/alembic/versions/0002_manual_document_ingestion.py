"""add manual document ingestion columns

Revision ID: 0002_manual_document_ingestion
Revises: 0001_document_metadata
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_manual_document_ingestion"
down_revision: str | None = "0001_document_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_legacy_subcategory(value: str | None) -> str:
    if value is None:
        return json.dumps(["unspecified"])

    normalized = value.strip()
    if normalized == "":
        return json.dumps(["unspecified"])

    return json.dumps([normalized])


def upgrade() -> None:
    op.add_column("documents", sa.Column("raw_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("word_count", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, subcategory FROM documents")).mappings().all()

    for row in rows:
        bind.execute(
            sa.text("UPDATE documents SET subcategory = :subcategory WHERE id = :id"),
            {
                "id": row["id"],
                "subcategory": _normalize_legacy_subcategory(row["subcategory"]),
            },
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "subcategory",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "subcategory",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            nullable=True,
        )

    op.drop_column("documents", "word_count")
    op.drop_column("documents", "raw_text")
