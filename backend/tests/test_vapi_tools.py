from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from app.models.doctor import Doctor
from app.models.vapi_tool_call import VapiToolCall


def next_open_date() -> date:
    value = date.today() + timedelta(days=1)
    while value.isoweekday() == 7:
        value += timedelta(days=1)
    return value


def test_vapi_tools_require_auth(client: TestClient) -> None:
    response = client.post("/vapi/tools/match-doctor", json={"symptoms": "eye pain"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_match_doctor_by_symptoms(client: TestClient, vapi_headers: dict[str, str]) -> None:
    response = client.post(
        "/vapi/tools/match-doctor",
        headers=vapi_headers,
        json={"symptoms": "eye pain and blurry vision"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["doctor_name"] == "Dr. Ayesha Khan"
    assert data["specialty"] == "Ophthalmology"
    assert data["safety_note"] is None


def test_emergency_symptoms_do_not_return_normal_booking(client: TestClient, vapi_headers: dict[str, str]) -> None:
    response = client.post(
        "/vapi/tools/match-doctor",
        headers=vapi_headers,
        json={"symptoms": "severe chest pain and difficulty breathing"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["doctor_id"] is None
    assert "emergency" in data["safety_note"].lower()


def test_availability_booking_idempotency_and_double_booking(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    doctor = db_session.scalar(select(Doctor).where(Doctor.name == "Dr. Ayesha Khan"))
    assert doctor is not None

    appointment_date = next_open_date()
    availability = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": appointment_date.isoformat()},
    )

    assert availability.status_code == 200
    slots = availability.json()["available_slots"]
    assert slots

    booking_payload = {
        "patient_name": "Ali Khan",
        "phone": "+923001234567",
        "doctor_id": doctor.id,
        "date": appointment_date.isoformat(),
        "start_time": slots[0]["start_time"],
        "reason": "eye pain",
        "vapi_call_id": "call-001",
    }
    booking = client.post("/vapi/tools/book-appointment", headers=vapi_headers, json=booking_payload)

    assert booking.status_code == 200
    first_ref = booking.json()["appointment_ref"]
    assert first_ref.startswith("APT-")

    retry = client.post("/vapi/tools/book-appointment", headers=vapi_headers, json=booking_payload)
    assert retry.status_code == 200
    assert retry.json()["appointment_ref"] == first_ref

    double_booking_payload = {**booking_payload, "vapi_call_id": "call-002"}
    double_booking = client.post(
        "/vapi/tools/book-appointment",
        headers=vapi_headers,
        json=double_booking_payload,
    )
    assert double_booking.status_code == 422
    assert double_booking.json()["error"]["code"] == "validation_error"


def test_booking_tool_audit_redacts_pii(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    doctor = db_session.scalar(select(Doctor).where(Doctor.name == "Dr. Sara Ahmed"))
    assert doctor is not None

    appointment_date = next_open_date()
    availability = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": appointment_date.isoformat()},
    )
    slot = availability.json()["available_slots"][0]["start_time"]

    response = client.post(
        "/vapi/tools/book-appointment",
        headers=vapi_headers,
        json={
            "patient_name": "Hadia Khan",
            "phone": "+923001112222",
            "doctor_id": doctor.id,
            "date": appointment_date.isoformat(),
            "start_time": slot,
            "reason": "fever and cough",
            "vapi_call_id": "call-redaction",
        },
    )
    assert response.status_code == 200

    tool_call = db_session.scalar(
        select(VapiToolCall)
        .where(VapiToolCall.tool_name == "bookAppointment")
        .order_by(VapiToolCall.created_at.desc())
    )
    assert tool_call is not None
    assert tool_call.redacted_request["patient_name"] == "[REDACTED]"
    assert tool_call.redacted_request["phone"] == "[REDACTED]"
    assert tool_call.redacted_request["reason"] == "[REDACTED]"


def test_end_of_call_stores_encrypted_summary(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    response = client.post(
        "/vapi/events/end-of-call",
        headers=vapi_headers,
        json={
            "vapi_call_id": "call-summary",
            "channel": "vapi_web",
            "status": "ended",
            "summary": "Patient booked an eye appointment.",
        },
    )

    assert response.status_code == 200
    call_log = db_session.scalar(select(CallLog).where(CallLog.vapi_call_id == "call-summary"))
    assert call_log is not None
    assert call_log.summary_encrypted != "Patient booked an eye appointment."

