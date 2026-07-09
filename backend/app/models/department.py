from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, new_uuid, utcnow


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("hospital_id", "name", name="uq_departments_hospital_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    hospital = relationship("Hospital", back_populates="departments")
    doctors = relationship("Doctor", back_populates="department")

