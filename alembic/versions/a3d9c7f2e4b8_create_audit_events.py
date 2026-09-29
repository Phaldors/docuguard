"""create audit events

Revision ID: a3d9c7f2e4b8
Revises: f0b8d3e5c1a7
Create Date: 2026-09-29 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3d9c7f2e4b8"
down_revision: Union[str, Sequence[str], None] = "f0b8d3e5c1a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bundle_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("field_name", sa.String(length=32), nullable=True),
        sa.Column("prior_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('field_correction', 'case_decision')",
            name="ck_audit_events_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["document_bundles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_events_bundle_id"), "audit_events", ["bundle_id"]
    )
    op.create_index(
        op.f("ix_audit_events_document_id"), "audit_events", ["document_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_audit_events_document_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_bundle_id"), table_name="audit_events")
    op.drop_table("audit_events")
