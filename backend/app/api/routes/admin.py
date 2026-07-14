from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_admin_auth
from app.core.security import pii_cipher
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.call_log import CallLog
from app.models.doctor import Doctor
from app.models.doctor_schedule import DoctorSchedule
from app.models.patient import Patient
from app.schemas.admin import (
    AppointmentListItem,
    AppointmentStatusUpdate,
    CallLogListItem,
    DashboardSummary,
    DoctorListItem,
    DoctorScheduleListItem,
)
from app.services.errors import NotFoundError, ValidationServiceError

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_auth)])

ALLOWED_APPOINTMENT_STATUSES = {
    "booked",
    "confirmed",
    "completed",
    "cancelled",
    "no_show",
    "rescheduled",
}

ACTIVE_APPOINTMENT_STATUSES = {"booked", "confirmed"}
DAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return "Not provided"
    if len(phone) <= 5:
        return "***"
    return f"{phone[:3]}***{phone[-2:]}"


def _appointment_end_time(start_time, duration_minutes: int):
    return (datetime.combine(date.today(), start_time) + timedelta(minutes=duration_minutes)).time()


def _call_duration_seconds(call_log: CallLog) -> int | None:
    if call_log.started_at is None or call_log.ended_at is None:
        return None
    return max(0, int((call_log.ended_at - call_log.started_at).total_seconds()))


def _call_appointment_ref(db: DbSession, call_log: CallLog) -> str | None:
    if call_log.appointment_id is None:
        return None
    appointment = db.scalar(select(Appointment).where(Appointment.id == call_log.appointment_id))
    return appointment.appointment_ref if appointment else None


def _appointment_item(appointment: Appointment, doctor: Doctor, patient: Patient) -> AppointmentListItem:
    patient_name = pii_cipher.decrypt(patient.full_name_encrypted) or "Unknown patient"
    patient_phone = pii_cipher.decrypt(patient.phone_encrypted)
    reason = pii_cipher.decrypt(appointment.reason_encrypted)

    return AppointmentListItem(
        id=appointment.id,
        appointment_ref=appointment.appointment_ref,
        patient_id=patient.id,
        patient_name=patient_name,
        patient_phone_masked=_mask_phone(patient_phone),
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        specialty=doctor.specialty,
        department=doctor.department.name,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time,
        end_time=_appointment_end_time(appointment.start_time, appointment.duration_minutes),
        duration_minutes=appointment.duration_minutes,
        reason_preview=reason[:120] if reason else None,
        status=appointment.status,
        source=appointment.source,
        created_at=appointment.created_at,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession) -> DashboardSummary:
    today = datetime.now(timezone.utc).date()
    return DashboardSummary(
        doctors=db.scalar(select(func.count(Doctor.id))) or 0,
        active_doctors=db.scalar(select(func.count(Doctor.id)).where(Doctor.active.is_(True))) or 0,
        patients=db.scalar(select(func.count(Patient.id))) or 0,
        appointments=db.scalar(select(func.count(Appointment.id))) or 0,
        todays_appointments=db.scalar(
            select(func.count(Appointment.id)).where(Appointment.appointment_date == today)
        )
        or 0,
        upcoming_appointments=db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.appointment_date >= today,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
        )
        or 0,
        booked_appointments=db.scalar(
            select(func.count(Appointment.id)).where(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
        )
        or 0,
        completed_appointments=db.scalar(
            select(func.count(Appointment.id)).where(Appointment.status == "completed")
        )
        or 0,
        cancelled_appointments=db.scalar(
            select(func.count(Appointment.id)).where(Appointment.status == "cancelled")
        )
        or 0,
        call_logs=db.scalar(select(func.count(CallLog.id))) or 0,
        calls_today=db.scalar(select(func.count(CallLog.id)).where(func.date(CallLog.created_at) == today)) or 0,
    )


@router.get("/appointments", response_model=list[AppointmentListItem])
def list_appointments(db: DbSession) -> list[AppointmentListItem]:
    rows = db.execute(
        select(Appointment, Doctor, Patient)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
    ).all()
    return [
        _appointment_item(appointment=appointment, doctor=doctor, patient=patient)
        for appointment, doctor, patient in rows
    ]


@router.patch("/appointments/{appointment_id}", response_model=AppointmentListItem)
def update_appointment_status(
    appointment_id: str,
    payload: AppointmentStatusUpdate,
    db: DbSession,
) -> AppointmentListItem:
    if payload.status not in ALLOWED_APPOINTMENT_STATUSES:
        raise ValidationServiceError("Unsupported appointment status.")

    appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
    if appointment is None:
        raise NotFoundError("Appointment was not found.")

    row = db.execute(
        select(Doctor, Patient)
        .join(Patient, Patient.id == appointment.patient_id)
        .where(Doctor.id == appointment.doctor_id)
    ).first()
    previous_status = appointment.status
    appointment.status = payload.status
    db.add(
        AuditLog(
            appointment_id=appointment.id,
            action="appointment.status_updated",
            target_type="appointment",
            target_id=appointment.id,
            metadata_json={"from": previous_status, "to": payload.status},
        )
    )
    db.commit()
    db.refresh(appointment)

    if row is None:
        raise NotFoundError("Appointment relationships were not found.")
    doctor, patient = row

    return _appointment_item(appointment=appointment, doctor=doctor, patient=patient)


@router.get("/doctors", response_model=list[DoctorListItem])
def list_doctors(db: DbSession) -> list[DoctorListItem]:
    rows = db.execute(
        select(Doctor, func.count(Appointment.id))
        .outerjoin(Appointment, Appointment.doctor_id == Doctor.id)
        .where(Doctor.active.is_(True))
        .group_by(Doctor.id)
        .order_by(Doctor.name.asc())
    ).all()
    return [
        DoctorListItem(
            id=doctor.id,
            name=doctor.name,
            specialty=doctor.specialty,
            department=doctor.department.name,
            active=doctor.active,
            appointment_count=appointment_count,
        )
        for doctor, appointment_count in rows
    ]


@router.get("/doctor-schedules", response_model=list[DoctorScheduleListItem])
def list_doctor_schedules(db: DbSession) -> list[DoctorScheduleListItem]:
    rows = db.execute(
        select(DoctorSchedule, Doctor)
        .join(Doctor, DoctorSchedule.doctor_id == Doctor.id)
        .where(Doctor.active.is_(True))
        .order_by(Doctor.name.asc(), DoctorSchedule.day_of_week.asc(), DoctorSchedule.start_time.asc())
    ).all()
    return [
        DoctorScheduleListItem(
            id=schedule.id,
            doctor_id=doctor.id,
            doctor_name=doctor.name,
            specialty=doctor.specialty,
            day_of_week=schedule.day_of_week,
            day_name=DAY_NAMES.get(schedule.day_of_week, "Unknown"),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            slot_duration_minutes=schedule.slot_duration_minutes,
            active=schedule.active,
        )
        for schedule, doctor in rows
    ]


@router.get("/call-logs", response_model=list[CallLogListItem])
def list_call_logs(db: DbSession) -> list[CallLogListItem]:
    rows = db.scalars(select(CallLog).order_by(CallLog.created_at.desc())).all()
    return [
        CallLogListItem(
            id=call_log.id,
            vapi_call_id=call_log.vapi_call_id,
            channel=call_log.channel,
            status=call_log.status,
            caller_phone_masked=_mask_phone(pii_cipher.decrypt(call_log.caller_phone_encrypted)),
            intent=call_log.intent,
            resolution_status=call_log.resolution_status,
            escalated=call_log.escalated,
            escalation_reason=call_log.escalation_reason,
            appointment_ref=_call_appointment_ref(db, call_log),
            has_summary=call_log.summary_encrypted is not None,
            has_transcript=call_log.transcript_encrypted is not None,
            duration_seconds=_call_duration_seconds(call_log),
            started_at=call_log.started_at,
            ended_at=call_log.ended_at,
            created_at=call_log.created_at,
        )
        for call_log in rows
    ]
