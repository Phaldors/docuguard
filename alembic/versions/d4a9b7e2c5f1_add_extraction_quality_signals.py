"""add extraction quality signals

Revision ID: d4a9b7e2c5f1
Revises: c2e7d4f8a6b1
Create Date: 2026-09-29 03:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a9b7e2c5f1"
down_revision: Union[str, Sequence[str], None] = "c2e7d4f8a6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "document_extractions",
        sa.Column(
            "quality_status",
            sa.String(length=32),
            server_default=sa.text("'complete'"),
            nullable=False,
        ),
    )
    op.add_column(
        "document_extractions",
        sa.Column("quality_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("document_extractions", "quality_note")
    op.drop_column("document_extractions", "quality_status")
