"""create llm traces

Revision ID: c8f4a2e1b9d3
Revises: a3d9c7f2e4b8
Create Date: 2026-09-29 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f4a2e1b9d3"
down_revision: Union[str, Sequence[str], None] = "a3d9c7f2e4b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "llm_traces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("call_type", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('success', 'error')", name="ck_llm_traces_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_traces_call_type"), "llm_traces", ["call_type"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_llm_traces_call_type"), table_name="llm_traces")
    op.drop_table("llm_traces")
