"""add call handling fields

Revision ID: 20260714_0002
Revises: 20260710_0001
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260714_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("call_logs", sa.Column("caller_phone_encrypted", sa.Text(), nullable=True))
    op.add_column("call_logs", sa.Column("caller_phone_hash", sa.String(length=64), nullable=True))
    op.add_column("call_logs", sa.Column("intent", sa.String(length=100), nullable=False, server_default="unknown"))
    op.add_column(
        "call_logs",
        sa.Column("resolution_status", sa.String(length=50), nullable=False, server_default="open"),
    )
    op.add_column("call_logs", sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("call_logs", sa.Column("escalation_reason", sa.String(length=255), nullable=True))
    op.add_column("call_logs", sa.Column("appointment_id", sa.String(length=36), nullable=True))
    op.add_column(
        "call_logs",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_call_logs_caller_phone_hash", "call_logs", ["caller_phone_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_call_logs_caller_phone_hash", table_name="call_logs")
    op.drop_column("call_logs", "updated_at")
    op.drop_column("call_logs", "appointment_id")
    op.drop_column("call_logs", "escalation_reason")
    op.drop_column("call_logs", "escalated")
    op.drop_column("call_logs", "resolution_status")
    op.drop_column("call_logs", "intent")
    op.drop_column("call_logs", "caller_phone_hash")
    op.drop_column("call_logs", "caller_phone_encrypted")
