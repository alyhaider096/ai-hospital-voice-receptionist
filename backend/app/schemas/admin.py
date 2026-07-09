from datetime import date, datetime, time

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    doctors: int
    patients: int
    appointments: int
    call_logs: int


class AppointmentListItem(BaseModel):
    id: str
    appointment_ref: str
    doctor_id: str
    doctor_name: str
    appointment_date: date
    start_time: time
    status: str
    source: str


class AppointmentStatusUpdate(BaseModel):
    status: str


class DoctorListItem(BaseModel):
    id: str
    name: str
    specialty: str
    department: str
    active: bool


class CallLogListItem(BaseModel):
    id: str
    vapi_call_id: str
    channel: str
    status: str
    has_summary: bool
    has_transcript: bool
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
