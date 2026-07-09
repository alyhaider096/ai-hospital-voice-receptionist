import hashlib
from datetime import date, time

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import normalize_phone, phone_hash, pii_cipher
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.vapi import BookAppointmentResponse
from app.services.availability import ensure_slot_available, get_doctor_or_404
from app.services.errors import SlotUnavailableError


def _idempotency_key(
    *,
    phone_hash_value: str,
    doctor_id: str,
    appointment_date: date,
    start_time: time,
    vapi_call_id: str | None,
) -> str:
    raw = "|".join(
        [
            vapi_call_id or "no-call-id",
            phone_hash_value,
            doctor_id,
            appointment_date.isoformat(),
            start_time.strftime("%H:%M"),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _next_appointment_ref(db: Session) -> str:
    count = db.scalar(select(func.count(Appointment.id))) or 0
    number = 10001 + int(count)
    while db.scalar(select(Appointment.id).where(Appointment.appointment_ref == f"APT-{number}")):
        number += 1
    return f"APT-{number}"


def book_appointment(
    db: Session,
    *,
    patient_name: str,
    phone: str,
    doctor_id: str,
    appointment_date: date,
    start_time: time,
    reason: str,
    vapi_call_id: str | None = None,
    source: str = "vapi_web",
) -> BookAppointmentResponse:
    get_doctor_or_404(db, doctor_id)
    normalized_phone = normalize_phone(phone)
    phone_hash_value = phone_hash(normalized_phone)
    idempotency_key = _idempotency_key(
        phone_hash_value=phone_hash_value,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        start_time=start_time,
        vapi_call_id=vapi_call_id,
    )

    existing = db.scalar(select(Appointment).where(Appointment.idempotency_key == idempotency_key))
    if existing:
        return BookAppointmentResponse(
            status=existing.status,
            appointment_ref=existing.appointment_ref,
            message="Appointment confirmed.",
        )

    ensure_slot_available(db, doctor_id, appointment_date, start_time)

    patient = db.scalar(select(Patient).where(Patient.phone_hash == phone_hash_value))
    if patient is None:
        patient = Patient(
            full_name_encrypted=pii_cipher.encrypt(patient_name) or "",
            phone_encrypted=pii_cipher.encrypt(normalized_phone) or "",
            phone_hash=phone_hash_value,
        )
        db.add(patient)
        db.flush()

    appointment = Appointment(
        appointment_ref=_next_appointment_ref(db),
        patient_id=patient.id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        start_time=start_time,
        duration_minutes=30,
        reason_encrypted=pii_cipher.encrypt(reason),
        status="booked",
        source=source,
        idempotency_key=idempotency_key,
    )
    db.add(appointment)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SlotUnavailableError("Slot is already booked.") from exc

    return BookAppointmentResponse(
        status="booked",
        appointment_ref=appointment.appointment_ref,
        message="Appointment confirmed.",
    )

