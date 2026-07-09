from datetime import date, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import pii_cipher
from app.models.appointment import Appointment
from app.models.call_log import CallLog
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.schedule_exception import ScheduleException
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


def test_vapi_tools_reject_wrong_token(client: TestClient) -> None:
    response = client.post(
        "/vapi/tools/match-doctor",
        headers={"Authorization": "Bearer wrong-token"},
        json={"symptoms": "eye pain"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Invalid Vapi token."


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


def test_unknown_symptoms_fallback_to_general_physician(
    client: TestClient,
    vapi_headers: dict[str, str],
) -> None:
    response = client.post(
        "/vapi/tools/match-doctor",
        headers=vapi_headers,
        json={"symptoms": "mild tiredness and general weakness"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["doctor_name"] == "Dr. Sara Ahmed"
    assert data["specialty"] == "General Physician"


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


def test_check_availability_rejects_past_date(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    doctor = db_session.scalar(select(Doctor).where(Doctor.name == "Dr. Ayesha Khan"))
    assert doctor is not None

    response = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": (date.today() - timedelta(days=1)).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Appointment date cannot be in the past."


def test_check_availability_rejects_unknown_doctor(
    client: TestClient,
    vapi_headers: dict[str, str],
) -> None:
    response = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": "missing-doctor-id", "date": next_open_date().isoformat()},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Doctor was not found or is inactive."


def test_schedule_exception_blocks_and_extra_slot_is_returned(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    doctor = db_session.scalar(select(Doctor).where(Doctor.name == "Dr. Ayesha Khan"))
    assert doctor is not None
    appointment_date = next_open_date()

    db_session.add(
        ScheduleException(
            doctor_id=doctor.id,
            exception_date=appointment_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            type="blocked",
            reason="Doctor meeting",
        )
    )
    db_session.add(
        ScheduleException(
            doctor_id=doctor.id,
            exception_date=appointment_date,
            start_time=time(18, 0),
            end_time=time(18, 30),
            type="extra",
            reason="Extra evening slot",
        )
    )
    db_session.commit()

    response = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": appointment_date.isoformat()},
    )

    assert response.status_code == 200
    slots = {slot["start_time"] for slot in response.json()["available_slots"]}
    assert "10:00" not in slots
    assert "10:30" not in slots
    assert "18:00" in slots


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


def test_cancelled_appointment_reopens_slot(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    doctor = db_session.scalar(select(Doctor).where(Doctor.name == "Dr. Ayesha Khan"))
    assert doctor is not None
    appointment_date = next_open_date()

    availability = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": appointment_date.isoformat()},
    )
    slot = availability.json()["available_slots"][0]["start_time"]
    booking = client.post(
        "/vapi/tools/book-appointment",
        headers=vapi_headers,
        json={
            "patient_name": "Cancel Test",
            "phone": "+923009990001",
            "doctor_id": doctor.id,
            "date": appointment_date.isoformat(),
            "start_time": slot,
            "reason": "eye pain",
            "vapi_call_id": "call-cancel",
        },
    )
    assert booking.status_code == 200

    appointment = db_session.scalar(
        select(Appointment).where(Appointment.appointment_ref == booking.json()["appointment_ref"])
    )
    assert appointment is not None
    status_update = client.patch(
        f"/admin/appointments/{appointment.id}",
        headers=admin_headers,
        json={"status": "cancelled"},
    )
    assert status_update.status_code == 200

    reopened = client.post(
        "/vapi/tools/check-availability",
        headers=vapi_headers,
        json={"doctor_id": doctor.id, "date": appointment_date.isoformat()},
    )
    assert slot in {available_slot["start_time"] for available_slot in reopened.json()["available_slots"]}


def test_patient_pii_is_encrypted_and_phone_hash_reuses_patient(
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
    slots = availability.json()["available_slots"]

    for index, phone in enumerate(["+92 300 555 0001", "+923005550001"]):
        response = client.post(
            "/vapi/tools/book-appointment",
            headers=vapi_headers,
            json={
                "patient_name": "Encrypted Patient",
                "phone": phone,
                "doctor_id": doctor.id,
                "date": appointment_date.isoformat(),
                "start_time": slots[index]["start_time"],
                "reason": "fever and cough",
                "vapi_call_id": f"call-pii-{index}",
            },
        )
        assert response.status_code == 200

    assert db_session.scalar(select(func.count(Patient.id))) == 1
    patient = db_session.scalar(select(Patient))
    assert patient is not None
    assert patient.full_name_encrypted != "Encrypted Patient"
    assert patient.phone_encrypted != "+923005550001"
    assert pii_cipher.decrypt(patient.full_name_encrypted) == "Encrypted Patient"
    assert pii_cipher.decrypt(patient.phone_encrypted) == "+923005550001"


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


def test_end_of_call_updates_existing_log_without_duplicate(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> None:
    for status in ["started", "ended"]:
        response = client.post(
            "/vapi/events/end-of-call",
            headers=vapi_headers,
            json={
                "vapi_call_id": "call-repeat",
                "channel": "vapi_web",
                "status": status,
                "summary": f"Call {status}",
            },
        )
        assert response.status_code == 200

    logs = db_session.scalars(select(CallLog).where(CallLog.vapi_call_id == "call-repeat")).all()
    assert len(logs) == 1
    assert logs[0].status == "ended"
