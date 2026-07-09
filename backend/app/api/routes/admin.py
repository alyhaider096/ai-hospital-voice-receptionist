from sqlalchemy import func, select

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_admin_auth
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.call_log import CallLog
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.admin import (
    AppointmentListItem,
    AppointmentStatusUpdate,
    CallLogListItem,
    DashboardSummary,
    DoctorListItem,
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


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession) -> DashboardSummary:
    return DashboardSummary(
        doctors=db.scalar(select(func.count(Doctor.id))) or 0,
        patients=db.scalar(select(func.count(Patient.id))) or 0,
        appointments=db.scalar(select(func.count(Appointment.id))) or 0,
        call_logs=db.scalar(select(func.count(CallLog.id))) or 0,
    )


@router.get("/appointments", response_model=list[AppointmentListItem])
def list_appointments(db: DbSession) -> list[AppointmentListItem]:
    rows = db.execute(select(Appointment, Doctor).join(Doctor, Appointment.doctor_id == Doctor.id)).all()
    return [
        AppointmentListItem(
            id=appointment.id,
            appointment_ref=appointment.appointment_ref,
            doctor_id=doctor.id,
            doctor_name=doctor.name,
            appointment_date=appointment.appointment_date,
            start_time=appointment.start_time,
            status=appointment.status,
            source=appointment.source,
        )
        for appointment, doctor in rows
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

    doctor = db.scalar(select(Doctor).where(Doctor.id == appointment.doctor_id))
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

    if doctor is None:
        raise NotFoundError("Doctor was not found.")

    return AppointmentListItem(
        id=appointment.id,
        appointment_ref=appointment.appointment_ref,
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time,
        status=appointment.status,
        source=appointment.source,
    )


@router.get("/doctors", response_model=list[DoctorListItem])
def list_doctors(db: DbSession) -> list[DoctorListItem]:
    rows = db.execute(select(Doctor).where(Doctor.active.is_(True))).scalars().all()
    return [
        DoctorListItem(
            id=doctor.id,
            name=doctor.name,
            specialty=doctor.specialty,
            department=doctor.department.name,
            active=doctor.active,
        )
        for doctor in rows
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
            has_summary=call_log.summary_encrypted is not None,
            has_transcript=call_log.transcript_encrypted is not None,
            started_at=call_log.started_at,
            ended_at=call_log.ended_at,
            created_at=call_log.created_at,
        )
        for call_log in rows
    ]
