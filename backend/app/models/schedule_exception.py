from datetime import date, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class ScheduleException(Base):
    __tablename__ = "schedule_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    doctor = relationship("Doctor", back_populates="schedule_exceptions")

