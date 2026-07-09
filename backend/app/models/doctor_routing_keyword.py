from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class DoctorRoutingKeyword(Base):
    __tablename__ = "doctor_routing_keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    emergency_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    doctor = relationship("Doctor", back_populates="routing_keywords")

