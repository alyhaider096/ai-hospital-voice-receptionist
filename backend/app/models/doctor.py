from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    department = relationship("Department", back_populates="doctors")
    routing_keywords = relationship("DoctorRoutingKeyword", back_populates="doctor")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    schedule_exceptions = relationship("ScheduleException", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

