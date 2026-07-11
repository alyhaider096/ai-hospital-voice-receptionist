from datetime import date, datetime, time

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    doctors: int
    active_doctors: int
    patients: int
    appointments: int
    todays_appointments: int
    upcoming_appointments: int
    booked_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    call_logs: int
    calls_today: int


class AppointmentListItem(BaseModel):
    id: str
    appointment_ref: str
    patient_id: str
    patient_name: str
    patient_phone_masked: str
    doctor_id: str
    doctor_name: str
    specialty: str
    department: str
    appointment_date: date
    start_time: time
    end_time: time
    duration_minutes: int
    reason_preview: str | None
    status: str
    source: str
    created_at: datetime


class AppointmentStatusUpdate(BaseModel):
    status: str


class DoctorListItem(BaseModel):
    id: str
    name: str
    specialty: str
    department: str
    active: bool
    appointment_count: int


class DoctorScheduleListItem(BaseModel):
    id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    day_of_week: int
    day_name: str
    start_time: time
    end_time: time
    slot_duration_minutes: int
    active: bool


class CallLogListItem(BaseModel):
    id: str
    vapi_call_id: str
    channel: str
    status: str
    has_summary: bool
    has_transcript: bool
    duration_seconds: int | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
