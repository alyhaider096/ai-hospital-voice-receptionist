from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.doctor import Doctor
from app.models.doctor_routing_keyword import DoctorRoutingKeyword
from app.schemas.vapi import MatchDoctorResponse
from app.services.errors import NotFoundError


EMERGENCY_MESSAGE = (
    "Please contact emergency services or visit the emergency department immediately."
)


def match_doctor_by_symptoms(db: Session, symptoms: str) -> MatchDoctorResponse:
    normalized = symptoms.lower()

    keywords = db.scalars(
        select(DoctorRoutingKeyword)
        .options(
            joinedload(DoctorRoutingKeyword.doctor).joinedload(Doctor.department),
        )
        .join(Doctor)
        .where(Doctor.active.is_(True))
        .order_by(DoctorRoutingKeyword.emergency_flag.desc(), DoctorRoutingKeyword.priority.asc())
    ).all()

    for keyword in keywords:
        if keyword.emergency_flag and keyword.keyword.lower() in normalized:
            return MatchDoctorResponse(
                doctor_id=None,
                doctor_name=None,
                specialty=None,
                department=None,
                reason="Symptoms may need urgent care.",
                safety_note=EMERGENCY_MESSAGE,
            )

    for keyword in keywords:
        if not keyword.emergency_flag and keyword.keyword.lower() in normalized:
            doctor = keyword.doctor
            return MatchDoctorResponse(
                doctor_id=doctor.id,
                doctor_name=doctor.name,
                specialty=doctor.specialty,
                department=doctor.department.name,
                reason=f"Matched because patient mentioned {keyword.keyword}.",
                safety_note=None,
            )

    fallback = db.scalar(
        select(Doctor)
        .options(joinedload(Doctor.department))
        .where(Doctor.active.is_(True), Doctor.specialty == "General Physician")
        .limit(1)
    )
    if fallback is None:
        raise NotFoundError("No active doctor is available for routing.")

    return MatchDoctorResponse(
        doctor_id=fallback.id,
        doctor_name=fallback.name,
        specialty=fallback.specialty,
        department=fallback.department.name,
        reason="No specific keyword matched, so the patient was routed to a general physician.",
        safety_note=None,
    )

