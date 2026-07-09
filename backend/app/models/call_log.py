from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    vapi_call_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    summary_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    tool_calls = relationship("VapiToolCall", back_populates="call_log")

