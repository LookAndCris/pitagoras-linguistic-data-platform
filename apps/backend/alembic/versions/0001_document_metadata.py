"""create document metadata table

Revision ID: 0001_document_metadata
Revises:
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_document_metadata"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("subcategory", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("doc_id", name="uq_documents_doc_id"),
    )


def downgrade() -> None:
    op.drop_table("documents")
