# Backend

FastAPI backend for the AI Hospital Voice Receptionist.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

## Implemented Endpoints

```txt
GET  /health
POST /vapi/tools/match-doctor
POST /vapi/tools/check-availability
POST /vapi/tools/book-appointment
POST /vapi/events/end-of-call
GET  /admin/dashboard/summary
GET  /admin/appointments
PATCH /admin/appointments/{id}
GET  /admin/doctors
```

Vapi endpoints require:

```txt
Authorization: Bearer <VAPI_TOOL_SECRET>
```

Admin endpoints currently require:

```txt
Authorization: Bearer <ADMIN_API_TOKEN>
```

The dashboard build can replace this temporary admin token with HttpOnly
session-cookie auth.

## Tests

```bash
pytest
```

Current tests cover Vapi auth, doctor matching, emergency routing,
availability, booking idempotency, double-booking rejection, PII redaction, and
admin summary auth.
