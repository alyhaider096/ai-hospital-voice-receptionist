from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    vapi_call_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    caller_phone_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    caller_phone_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    intent: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    escalation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appointment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    tool_calls = relationship("VapiToolCall", back_populates="call_log")
