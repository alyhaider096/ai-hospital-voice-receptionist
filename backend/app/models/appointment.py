from datetime import date, time

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointments_active_slot",
            "doctor_id",
            "appointment_date",
            "start_time",
            unique=True,
            postgresql_where=text("status NOT IN ('cancelled', 'rescheduled', 'no_show')"),
            sqlite_where=text("status NOT IN ('cancelled', 'rescheduled', 'no_show')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    appointment_ref: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    reason_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="booked")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="vapi_web")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    audit_logs = relationship("AuditLog", back_populates="appointment")
