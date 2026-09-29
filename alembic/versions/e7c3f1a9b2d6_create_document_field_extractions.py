"""create document field extractions

Revision ID: e7c3f1a9b2d6
Revises: d4a9b7e2c5f1
Create Date: 2026-09-29 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c3f1a9b2d6"
down_revision: Union[str, Sequence[str], None] = "d4a9b7e2c5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "document_field_extractions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("supplier_name_value", sa.Text(), nullable=True),
        sa.Column("supplier_name_evidence", sa.Text(), nullable=True),
        sa.Column("supplier_name_confidence", sa.Float(), nullable=False),
        sa.Column("document_number_value", sa.Text(), nullable=True),
        sa.Column("document_number_evidence", sa.Text(), nullable=True),
        sa.Column("document_number_confidence", sa.Float(), nullable=False),
        sa.Column("document_date_value", sa.Text(), nullable=True),
        sa.Column("document_date_evidence", sa.Text(), nullable=True),
        sa.Column("document_date_confidence", sa.Float(), nullable=False),
        sa.Column("currency_value", sa.Text(), nullable=True),
        sa.Column("currency_evidence", sa.Text(), nullable=True),
        sa.Column("currency_confidence", sa.Float(), nullable=False),
        sa.Column("total_value", sa.Text(), nullable=True),
        sa.Column("total_evidence", sa.Text(), nullable=True),
        sa.Column("total_confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("document_field_extractions")
