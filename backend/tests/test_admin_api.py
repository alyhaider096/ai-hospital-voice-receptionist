from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.doctor import Doctor


def next_open_date() -> date:
    value = date.today() + timedelta(days=1)
    while value.isoweekday() == 7:
        value += timedelta(days=1)
    return value


def create_test_appointment(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
) -> Appointment:
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
            "patient_name": "Admin Test",
            "phone": "+923001230000",
            "doctor_id": doctor.id,
            "date": appointment_date.isoformat(),
            "start_time": slot,
            "reason": "eye pain",
            "vapi_call_id": "admin-test-call",
        },
    )
    assert booking.status_code == 200
    appointment = db_session.scalar(
        select(Appointment).where(Appointment.appointment_ref == booking.json()["appointment_ref"])
    )
    assert appointment is not None
    return appointment


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_returns_admin_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "change-this-password"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "replace-with-long-random-admin-token"
    assert response.json()["role"] == "admin"


def test_login_rejects_bad_credentials(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_logout_returns_ok(client: TestClient) -> None:
    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_summary_requires_auth(client: TestClient) -> None:
    response = client.get("/admin/dashboard/summary")

    assert response.status_code == 401


def test_admin_summary_returns_counts(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/admin/dashboard/summary", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["doctors"] == 5
    assert data["active_doctors"] == 5
    assert data["patients"] == 0
    assert data["appointments"] == 0
    assert data["todays_appointments"] == 0
    assert data["upcoming_appointments"] == 0
    assert data["booked_appointments"] == 0
    assert data["completed_appointments"] == 0
    assert data["cancelled_appointments"] == 0
    assert data["call_logs"] == 0
    assert data["calls_today"] == 0


def test_admin_doctors_lists_seeded_active_doctors(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get("/admin/doctors", headers=admin_headers)

    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) == 5
    assert {doctor["specialty"] for doctor in doctors} >= {"Ophthalmology", "General Physician"}
    assert "appointment_count" in doctors[0]


def test_admin_doctor_schedules_lists_seeded_schedule_blocks(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get("/admin/doctor-schedules", headers=admin_headers)

    assert response.status_code == 200
    schedules = response.json()
    assert len(schedules) >= 5
    assert schedules[0]["day_name"] in {
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    }
    assert "doctor_name" in schedules[0]


def test_admin_appointments_and_status_update_write_audit_log(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    appointment = create_test_appointment(client, db_session, vapi_headers)

    list_response = client.get("/admin/appointments", headers=admin_headers)
    assert list_response.status_code == 200
    appointment_row = list_response.json()[0]
    assert appointment_row["appointment_ref"] == appointment.appointment_ref
    assert appointment_row["patient_name"] == "Admin Test"
    assert appointment_row["patient_phone_masked"].startswith("+92")
    assert appointment_row["reason_preview"] == "eye pain"
    assert appointment_row["duration_minutes"] == 30
    assert appointment_row["department"]

    update_response = client.patch(
        f"/admin/appointments/{appointment.id}",
        headers=admin_headers,
        json={"status": "confirmed"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "confirmed"

    audit_log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "appointment.status_updated")
    )
    assert audit_log is not None
    assert audit_log.metadata_json == {"from": "booked", "to": "confirmed"}


def test_admin_rejects_invalid_appointment_status(
    client: TestClient,
    db_session: Session,
    vapi_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    appointment = create_test_appointment(client, db_session, vapi_headers)

    response = client.patch(
        f"/admin/appointments/{appointment.id}",
        headers=admin_headers,
        json={"status": "made_up_status"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Unsupported appointment status."


def test_admin_call_logs_hide_summary_and_transcript(
    client: TestClient,
    vapi_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    call_response = client.post(
        "/vapi/events/end-of-call",
        headers=vapi_headers,
        json={
            "vapi_call_id": "admin-call-log",
            "channel": "vapi_web",
            "status": "ended",
            "summary": "Sensitive patient summary",
            "transcript": "Sensitive transcript",
        },
    )
    assert call_response.status_code == 200

    response = client.get("/admin/call-logs", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data[0]["vapi_call_id"] == "admin-call-log"
    assert data[0]["has_summary"] is True
    assert data[0]["has_transcript"] is True
    assert data[0]["duration_seconds"] is None
    assert "summary" not in data[0]
    assert "transcript" not in data[0]
