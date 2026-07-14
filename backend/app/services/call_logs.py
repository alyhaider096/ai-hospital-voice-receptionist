from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import normalize_phone, phone_hash, pii_cipher
from app.db.base import new_uuid
from app.models.appointment import Appointment
from app.models.call_log import CallLog
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.vapi import (
    CallerAppointmentSummary,
    CallerHistoryRequest,
    CallerHistoryResponse,
    ClassifyCallIntentRequest,
    ClassifyCallIntentResponse,
    EndOfCallRequest,
    EndOfCallResponse,
)

ESCALATION_INTENTS = {
    "billing_or_payment",
    "complaint",
    "emergency_or_urgent",
    "human_receptionist",
}

INTENT_KEYWORDS = {
    "emergency_or_urgent": [
        "emergency",
        "urgent",
        "severe",
        "heavy bleeding",
        "chest pain",
        "difficulty breathing",
        "vision loss",
        "accident",
        "unconscious",
    ],
    "complaint": [
        "complaint",
        "complain",
        "bad service",
        "rude",
        "unhappy",
        "not satisfied",
        "problem with staff",
    ],
    "billing_or_payment": [
        "payment",
        "billing",
        "bill",
        "invoice",
        "refund",
        "charges",
        "fee",
        "price",
    ],
    "human_receptionist": [
        "human",
        "receptionist",
        "representative",
        "staff member",
        "real person",
    ],
    "cancel_appointment": ["cancel", "delete appointment"],
    "reschedule_appointment": ["reschedule", "change appointment", "move appointment", "different time"],
    "doctor_availability": ["available", "availability", "schedule", "timing", "doctor time"],
    "new_appointment": ["book", "appointment", "visit", "see doctor", "consultation"],
}


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return "Not provided"
    if len(phone) <= 5:
        return "***"
    return f"{phone[:3]}***{phone[-2:]}"


def _call_id(vapi_call_id: str | None) -> str:
    return vapi_call_id or f"generated-{new_uuid()}"


def _apply_phone(call_log: CallLog, phone: str | None) -> None:
    if not phone:
        return
    normalized = normalize_phone(phone)
    call_log.caller_phone_encrypted = pii_cipher.encrypt(normalized)
    call_log.caller_phone_hash = phone_hash(normalized)


def _get_or_create_call_log(
    db: Session,
    *,
    vapi_call_id: str | None,
    channel: str = "vapi_voice",
    status: str = "active",
) -> CallLog:
    normalized_call_id = _call_id(vapi_call_id)
    call_log = db.scalar(select(CallLog).where(CallLog.vapi_call_id == normalized_call_id))
    if call_log is None:
        call_log = CallLog(vapi_call_id=normalized_call_id, channel=channel, status=status)
        db.add(call_log)
        db.flush()
    return call_log


def _appointment_summary(appointment: Appointment, doctor: Doctor) -> CallerAppointmentSummary:
    return CallerAppointmentSummary(
        appointment_ref=appointment.appointment_ref,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time.strftime("%H:%M"),
        doctor_name=doctor.name,
        specialty=doctor.specialty,
        status=appointment.status,
    )


def classify_intent_text(utterance: str) -> str:
    normalized = utterance.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "general_inquiry"


def classify_call_intent(db: Session, payload: ClassifyCallIntentRequest) -> ClassifyCallIntentResponse:
    intent = classify_intent_text(payload.utterance)
    escalation_required = intent in ESCALATION_INTENTS
    escalation_reason = f"{intent.replace('_', ' ')} requires human follow-up." if escalation_required else None
    resolution_status = "escalated" if escalation_required else "open"

    call_log = _get_or_create_call_log(db, vapi_call_id=payload.vapi_call_id)
    _apply_phone(call_log, payload.caller_phone)
    call_log.intent = intent
    call_log.resolution_status = resolution_status
    call_log.escalated = escalation_required
    call_log.escalation_reason = escalation_reason
    db.commit()

    if escalation_required:
        message = "This call should be offered to a human receptionist now."
    elif intent == "new_appointment":
        message = "Continue the appointment booking flow."
    elif intent == "cancel_appointment":
        message = "Collect appointment reference and confirm before cancelling."
    elif intent == "reschedule_appointment":
        message = "Collect appointment reference, preferred date, and preferred time before rescheduling."
    else:
        message = "Continue helping the caller and collect more details if needed."

    return ClassifyCallIntentResponse(
        intent=intent,
        resolution_status=resolution_status,
        escalation_required=escalation_required,
        escalation_reason=escalation_reason,
        message=message,
    )


def lookup_caller_history(db: Session, payload: CallerHistoryRequest) -> CallerHistoryResponse:
    normalized_phone = normalize_phone(payload.phone)
    phone_hash_value = phone_hash(normalized_phone)

    if payload.vapi_call_id:
        call_log = _get_or_create_call_log(db, vapi_call_id=payload.vapi_call_id)
        _apply_phone(call_log, normalized_phone)
        db.commit()

    patient = db.scalar(select(Patient).where(Patient.phone_hash == phone_hash_value))
    if patient is None:
        return CallerHistoryResponse(
            known_caller=False,
            phone_masked=_mask_phone(normalized_phone),
            appointment_count=0,
            upcoming_appointments=[],
            last_appointment=None,
            message="No previous patient record was found for this phone number.",
        )

    rows = db.execute(
        select(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .where(Appointment.patient_id == patient.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
    ).all()
    summaries = [_appointment_summary(appointment, doctor) for appointment, doctor in rows]
    upcoming = [
        summary
        for summary in summaries
        if summary.appointment_date >= date.today() and summary.status in {"booked", "confirmed"}
    ]
    message = (
        f"Caller has {len(summaries)} appointment record."
        if len(summaries) == 1
        else f"Caller has {len(summaries)} appointment records."
    )
    if upcoming:
        first = upcoming[0]
        message += f" Upcoming appointment: {first.appointment_ref} with {first.doctor_name}."

    return CallerHistoryResponse(
        known_caller=True,
        phone_masked=_mask_phone(normalized_phone),
        appointment_count=len(summaries),
        upcoming_appointments=upcoming[:3],
        last_appointment=summaries[0] if summaries else None,
        message=message,
    )


def link_call_to_booking(
    db: Session,
    *,
    vapi_call_id: str | None,
    phone: str,
    appointment_ref: str,
) -> None:
    if not vapi_call_id:
        return
    appointment = db.scalar(select(Appointment).where(Appointment.appointment_ref == appointment_ref))
    call_log = _get_or_create_call_log(db, vapi_call_id=vapi_call_id)
    _apply_phone(call_log, phone)
    call_log.intent = "new_appointment"
    call_log.resolution_status = "resolved"
    call_log.escalated = False
    call_log.escalation_reason = None
    call_log.appointment_id = appointment.id if appointment else None
    db.commit()


def save_end_of_call(db: Session, payload: EndOfCallRequest) -> EndOfCallResponse:
    call_log = _get_or_create_call_log(
        db,
        vapi_call_id=payload.vapi_call_id,
        channel=payload.channel,
        status=payload.status,
    )

    _apply_phone(call_log, payload.caller_phone)
    call_log.channel = payload.channel
    call_log.status = payload.status
    if payload.intent is not None:
        call_log.intent = payload.intent
    if payload.resolution_status is not None:
        call_log.resolution_status = payload.resolution_status
    if payload.escalated is not None:
        call_log.escalated = payload.escalated
    if payload.escalation_reason is not None:
        call_log.escalation_reason = payload.escalation_reason
    call_log.summary_encrypted = pii_cipher.encrypt(payload.summary)
    call_log.transcript_encrypted = pii_cipher.encrypt(payload.transcript)
    call_log.started_at = payload.started_at
    call_log.ended_at = payload.ended_at

    db.commit()
    return EndOfCallResponse(status="saved", message="Call log saved.")
