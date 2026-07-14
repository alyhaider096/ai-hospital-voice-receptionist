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
    requested_date_was_past: bool = False
    earliest_available_date: date | None = None
    earliest_available_start_time: str | None = None
    earliest_available_display_time: str | None = None
    next_available_summary: str | None = None
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
    appointment_ref_spoken: str
    message: str


class CallerHistoryRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=30)
    vapi_call_id: str | None = None


class CallerAppointmentSummary(BaseModel):
    appointment_ref: str
    appointment_date: date
    start_time: str
    doctor_name: str
    specialty: str
    status: str


class CallerHistoryResponse(BaseModel):
    known_caller: bool
    phone_masked: str
    appointment_count: int
    upcoming_appointments: list[CallerAppointmentSummary] = Field(default_factory=list)
    last_appointment: CallerAppointmentSummary | None = None
    message: str


class ClassifyCallIntentRequest(BaseModel):
    utterance: str = Field(min_length=2, max_length=2000)
    vapi_call_id: str | None = None
    caller_phone: str | None = Field(default=None, min_length=7, max_length=30)


class ClassifyCallIntentResponse(BaseModel):
    intent: str
    resolution_status: str
    escalation_required: bool
    escalation_reason: str | None = None
    message: str


class EndOfCallRequest(BaseModel):
    vapi_call_id: str
    channel: str = "vapi_web"
    status: str = "ended"
    caller_phone: str | None = None
    intent: str | None = None
    resolution_status: str | None = None
    escalated: bool | None = None
    escalation_reason: str | None = None
    summary: str | None = None
    transcript: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class EndOfCallResponse(BaseModel):
    status: str
    message: str
