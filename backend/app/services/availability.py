from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.doctor_schedule import DoctorSchedule
from app.models.schedule_exception import ScheduleException
from app.schemas.vapi import AvailableSlot
from app.services.errors import NotFoundError, ValidationServiceError

ACTIVE_APPOINTMENT_STATUSES = {"booked", "confirmed"}


def _combine(day: date, value: time) -> datetime:
    return datetime.combine(day, value)


def _format_display(value: time) -> str:
    return datetime.combine(date.today(), value).strftime("%I:%M %p").lstrip("0")


def _overlaps(start: time, end: time, block_start: time, block_end: time) -> bool:
    return start < block_end and end > block_start


def get_doctor_or_404(db: Session, doctor_id: str) -> Doctor:
    doctor = db.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.active.is_(True)))
    if doctor is None:
        raise NotFoundError("Doctor was not found or is inactive.")
    return doctor


def get_available_slots(db: Session, doctor_id: str, requested_date: date) -> list[AvailableSlot]:
    get_doctor_or_404(db, doctor_id)

    if requested_date < date.today():
        raise ValidationServiceError("Appointment date cannot be in the past.")

    schedules = db.scalars(
        select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.day_of_week == requested_date.isoweekday(),
            DoctorSchedule.active.is_(True),
        )
    ).all()

    exceptions = db.scalars(
        select(ScheduleException).where(
            ScheduleException.doctor_id == doctor_id,
            ScheduleException.exception_date == requested_date,
        )
    ).all()

    booked_times = {
        appointment.start_time
        for appointment in db.scalars(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == requested_date,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
        ).all()
    }

    slots: list[time] = []
    for schedule in schedules:
        cursor = _combine(requested_date, schedule.start_time)
        end = _combine(requested_date, schedule.end_time)
        step = timedelta(minutes=schedule.slot_duration_minutes)
        while cursor + step <= end:
            slot_start = cursor.time()
            slot_end = (cursor + step).time()
            blocked = any(
                exception.type in {"blocked", "leave", "holiday"}
                and _overlaps(slot_start, slot_end, exception.start_time, exception.end_time)
                for exception in exceptions
            )
            if not blocked and slot_start not in booked_times:
                slots.append(slot_start)
            cursor += step

    for exception in exceptions:
        if exception.type != "extra":
            continue
        cursor = _combine(requested_date, exception.start_time)
        end = _combine(requested_date, exception.end_time)
        step = timedelta(minutes=30)
        while cursor + step <= end:
            slot_start = cursor.time()
            if slot_start not in booked_times and slot_start not in slots:
                slots.append(slot_start)
            cursor += step

    return [
        AvailableSlot(start_time=slot.strftime("%H:%M"), display_time=_format_display(slot))
        for slot in sorted(slots)
    ]


def ensure_slot_available(db: Session, doctor_id: str, requested_date: date, start_time: time) -> None:
    slots = get_available_slots(db, doctor_id, requested_date)
    if start_time.strftime("%H:%M") not in {slot.start_time for slot in slots}:
        raise ValidationServiceError("Requested slot is not available.")

