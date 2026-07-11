from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_vapi_auth
from app.core.security import redact_payload
from app.models.vapi_tool_call import VapiToolCall
from app.schemas.vapi import (
    BookAppointmentRequest,
    BookAppointmentResponse,
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    EndOfCallRequest,
    EndOfCallResponse,
    MatchDoctorRequest,
    MatchDoctorResponse,
)
from app.services.availability import (
    NO_SLOT_HANDOFF_NOTE,
    get_available_slots,
    get_next_available_dates,
    should_recommend_handoff,
)
from app.services.booking import book_appointment
from app.services.call_logs import save_end_of_call
from app.services.matching import match_doctor_by_symptoms

router = APIRouter(prefix="/vapi", tags=["vapi"], dependencies=[Depends(require_vapi_auth)])


def _availability_summary(next_available_dates) -> str | None:
    if not next_available_dates:
        return None
    options = [
        f"{suggestion.display_date} at {suggestion.first_available_slot.display_time}"
        for suggestion in next_available_dates
    ]
    return "Next available options: " + "; ".join(options) + "."


def _availability_message(
    *,
    slots,
    next_available_dates,
    requested_date_was_past: bool,
    handoff_recommended: bool,
) -> str:
    summary = _availability_summary(next_available_dates)
    if slots:
        slot_text = ", ".join(slot.display_time for slot in slots[:3])
        return f"Available slots found for the requested date: {slot_text}."
    if requested_date_was_past:
        return (
            "The requested date appears to be in the past. "
            f"{summary or 'No future slots were found in the next two weeks.'}"
        )
    if handoff_recommended:
        return (
            "No standard slots are available for today or tomorrow. "
            f"{summary or 'No future slots were found in the next two weeks.'} "
            "For an urgent request, offer a human receptionist."
        )
    return (
        "No standard slots are available for the requested date. "
        f"{summary or 'No future slots were found in the next two weeks.'}"
    )


def _record_tool_call(
    db: DbSession,
    *,
    tool_name: str,
    status: str,
    request_payload: dict,
    response_payload: dict | None = None,
) -> None:
    db.add(
        VapiToolCall(
            tool_name=tool_name,
            status=status,
            redacted_request=redact_payload(request_payload),
            redacted_response=redact_payload(response_payload or {}),
        )
    )
    db.commit()


@router.post("/tools/match-doctor", response_model=MatchDoctorResponse)
def match_doctor(payload: MatchDoctorRequest, db: DbSession) -> MatchDoctorResponse:
    response = match_doctor_by_symptoms(db, payload.symptoms)
    _record_tool_call(
        db,
        tool_name="matchDoctorBySymptoms",
        status="success",
        request_payload=payload.model_dump(),
        response_payload=response.model_dump(),
    )
    return response


@router.post("/tools/check-availability", response_model=CheckAvailabilityResponse)
def check_availability(payload: CheckAvailabilityRequest, db: DbSession) -> CheckAvailabilityResponse:
    requested_date_was_past = payload.date < date.today()
    if requested_date_was_past:
        slots = []
        next_available_dates = get_next_available_dates(
            db,
            payload.doctor_id,
            after_date=date.today() - timedelta(days=1),
        )
    else:
        slots = get_available_slots(db, payload.doctor_id, payload.date)
        next_available_dates = [] if slots else get_next_available_dates(db, payload.doctor_id, after_date=payload.date)
    handoff_recommended = should_recommend_handoff(payload.date, slots)
    earliest_date = payload.date if slots else next_available_dates[0].date if next_available_dates else None
    earliest_slot = slots[0] if slots else next_available_dates[0].first_available_slot if next_available_dates else None
    next_available_summary = _availability_summary(next_available_dates)
    message = _availability_message(
        slots=slots,
        next_available_dates=next_available_dates,
        requested_date_was_past=requested_date_was_past,
        handoff_recommended=handoff_recommended,
    )
    response = CheckAvailabilityResponse(
        doctor_id=payload.doctor_id,
        date=payload.date,
        available_slots=slots,
        next_available_dates=next_available_dates,
        requested_date_was_past=requested_date_was_past,
        earliest_available_date=earliest_date,
        earliest_available_start_time=earliest_slot.start_time if earliest_slot else None,
        earliest_available_display_time=earliest_slot.display_time if earliest_slot else None,
        next_available_summary=next_available_summary,
        handoff_recommended=handoff_recommended,
        message=message,
        safe_handoff_note=NO_SLOT_HANDOFF_NOTE if handoff_recommended else None,
    )
    _record_tool_call(
        db,
        tool_name="checkAvailability",
        status="success",
        request_payload=payload.model_dump(mode="json"),
        response_payload=response.model_dump(mode="json"),
    )
    return response


@router.post("/tools/book-appointment", response_model=BookAppointmentResponse)
def create_appointment(payload: BookAppointmentRequest, db: DbSession) -> BookAppointmentResponse:
    response = book_appointment(
        db,
        patient_name=payload.patient_name,
        phone=payload.phone,
        doctor_id=payload.doctor_id,
        appointment_date=payload.date,
        start_time=payload.start_time,
        reason=payload.reason,
        vapi_call_id=payload.vapi_call_id,
        source="vapi_web",
    )
    _record_tool_call(
        db,
        tool_name="bookAppointment",
        status="success",
        request_payload=payload.model_dump(mode="json"),
        response_payload=response.model_dump(mode="json"),
    )
    return response


@router.post("/events/end-of-call", response_model=EndOfCallResponse)
def end_of_call(payload: EndOfCallRequest, db: DbSession) -> EndOfCallResponse:
    return save_end_of_call(db, payload)
