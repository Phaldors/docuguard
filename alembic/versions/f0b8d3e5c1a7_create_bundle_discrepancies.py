"""create bundle discrepancies

Revision ID: f0b8d3e5c1a7
Revises: e7c3f1a9b2d6
Create Date: 2026-09-29 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f0b8d3e5c1a7"
down_revision: Union[str, Sequence[str], None] = "e7c3f1a9b2d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bundle_discrepancies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bundle_id", sa.UUID(), nullable=False),
        sa.Column("discrepancy_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "document_ids", postgresql.ARRAY(sa.UUID()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["document_bundles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bundle_discrepancies_bundle_id"),
        "bundle_discrepancies",
        ["bundle_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_bundle_discrepancies_bundle_id"), table_name="bundle_discrepancies"
    )
    op.drop_table("bundle_discrepancies")
