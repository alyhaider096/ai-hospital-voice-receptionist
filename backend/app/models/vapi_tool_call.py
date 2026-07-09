from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class VapiToolCall(Base):
    __tablename__ = "vapi_tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    call_log_id: Mapped[str | None] = mapped_column(ForeignKey("call_logs.id"), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    redacted_request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    redacted_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    call_log = relationship("CallLog", back_populates="tool_calls")

