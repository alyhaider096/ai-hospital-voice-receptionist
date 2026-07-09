"""initial schema

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hospitals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)
    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("full_name_encrypted", sa.Text(), nullable=False),
        sa.Column("phone_encrypted", sa.Text(), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patients_phone_hash", "patients", ["phone_hash"], unique=True)
    op.create_table(
        "departments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("hospital_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hospital_id", "name", name="uq_departments_hospital_name"),
    )
    op.create_table(
        "call_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vapi_call_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary_encrypted", sa.Text(), nullable=True),
        sa.Column("transcript_encrypted", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_logs_vapi_call_id", "call_logs", ["vapi_call_id"], unique=True)
    op.create_table(
        "doctors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("department_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vapi_tool_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("call_log_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("redacted_request", sa.JSON(), nullable=True),
        sa.Column("redacted_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["call_log_id"], ["call_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "doctor_routing_keywords",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("emergency_flag", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "doctor_schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "schedule_exceptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("appointment_ref", sa.String(length=50), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("reason_encrypted", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_appointment_ref", "appointments", ["appointment_ref"], unique=True)
    op.create_index("ix_appointments_idempotency_key", "appointments", ["idempotency_key"], unique=True)
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["doctor_id", "appointment_date", "start_time"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('cancelled', 'rescheduled', 'no_show')"),
        sqlite_where=sa.text("status NOT IN ('cancelled', 'rescheduled', 'no_show')"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("appointment_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("uq_appointments_active_slot", table_name="appointments")
    op.drop_index("ix_appointments_idempotency_key", table_name="appointments")
    op.drop_index("ix_appointments_appointment_ref", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("schedule_exceptions")
    op.drop_table("doctor_schedules")
    op.drop_table("doctor_routing_keywords")
    op.drop_table("vapi_tool_calls")
    op.drop_table("doctors")
    op.drop_index("ix_call_logs_vapi_call_id", table_name="call_logs")
    op.drop_table("call_logs")
    op.drop_table("departments")
    op.drop_index("ix_patients_phone_hash", table_name="patients")
    op.drop_table("patients")
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")
    op.drop_table("hospitals")

