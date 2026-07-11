from datetime import date, datetime, time

from pydantic import BaseModel, Field


class MatchDoctorRequest(BaseModel):
    symptoms: str = Field(min_length=2, max_length=1000)


class MatchDoctorResponse(BaseModel):
    doctor_id: str | None
    doctor_name: str | None
    specialty: str | None
    department: str | None
    reason: str
    safety_note: str | None = None


class CheckAvailabilityRequest(BaseModel):
    doctor_id: str
    date: date


class AvailableSlot(BaseModel):
    start_time: str
    display_time: str


class SuggestedAvailability(BaseModel):
    date: date
    display_date: str
    first_available_slot: AvailableSlot


class CheckAvailabilityResponse(BaseModel):
    doctor_id: str
    date: date
    available_slots: list[AvailableSlot]
    next_available_dates: list[SuggestedAvailability] = Field(default_factory=list)
    handoff_recommended: bool = False
    message: str = "Available slots found."
    safe_handoff_note: str | None = None


class BookAppointmentRequest(BaseModel):
    patient_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=7, max_length=30)
    doctor_id: str
    date: date
    start_time: time
    reason: str = Field(min_length=2, max_length=1000)
    vapi_call_id: str | None = None


class BookAppointmentResponse(BaseModel):
    status: str
    appointment_ref: str
    message: str


class EndOfCallRequest(BaseModel):
    vapi_call_id: str
    channel: str = "vapi_web"
    status: str = "ended"
    summary: str | None = None
    transcript: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class EndOfCallResponse(BaseModel):
    status: str
    message: str
