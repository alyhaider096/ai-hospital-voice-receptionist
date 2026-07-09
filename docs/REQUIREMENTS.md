# Requirements

## Product Requirement

The system must act as an AI hospital voice receptionist that can safely handle
appointment booking workflows, maintain official appointment records, and give
staff a dashboard for operational follow-up.

## Functional Requirements

### Voice Receptionist

- Greet callers professionally.
- Ask for symptoms only for appointment routing.
- Collect patient name and phone.
- Ask for preferred appointment date.
- Match patient to a doctor or department.
- Offer available appointment slots.
- Ask for explicit confirmation before booking.
- Speak the appointment reference after booking.
- Save call summary after the call.
- Trigger emergency guidance for urgent symptoms.

### Doctor Matching

- Match symptoms to doctors through controlled routing keywords.
- Prefer active doctors only.
- Return the reason for the match.
- Return a safety note for emergency keywords.
- Never return a diagnosis.

### Availability

- Generate slots from doctor schedules.
- Exclude already-booked slots.
- Apply schedule exceptions.
- Reject past dates.
- Return API times in `HH:mm` format.
- Return display times separately for the assistant.

### Booking

- Create or reuse patient by phone hash.
- Encrypt patient name, phone, and appointment reason.
- Generate unique appointment reference.
- Prevent double booking with database constraints.
- Support idempotent retry from Vapi.
- Return clean JSON errors.

### Call Logs

- Store Vapi call ID.
- Store channel as `vapi_web` or `vapi_phone`.
- Store status, started time, ended time, and summary.
- Store transcript only if consent and retention policy allow it.

### Admin Dashboard

- Login/logout.
- View appointment summary.
- View appointments with filters.
- View appointment detail.
- Update appointment status.
- View doctors and schedules.
- View call logs.
- Write audit logs for important admin changes.

## Non-Functional Requirements

### Security

- Vapi tools require bearer-token authentication.
- Admin dashboard uses secure session cookies.
- PII is encrypted at rest.
- Phone lookup uses hash matching.
- Raw PII is never logged.
- Secrets are never committed.
- Admin actions are audited.

### Reliability

- Booking must be transaction-safe.
- Double-booking must fail even under concurrent requests.
- Tool retries must not create duplicate appointments.
- Clean errors must be returned to Vapi.

### Maintainability

- Backend routers stay thin.
- Business logic lives in service modules.
- Database changes go through Alembic migrations.
- Docs must be updated when schema or tool contracts change.

### Testing

- Unit tests for matching, availability, and booking.
- API tests for auth and Vapi tool contracts.
- Double-booking race test.
- Vapi Web Call test before official number.
- Dashboard smoke tests before client demo.

## Acceptance Checklist

```txt
[x] Doctor matching returns expected specialty
[x] Emergency symptoms return safety guidance
[x] Availability excludes booked slots
[x] Booking creates appointment reference
[x] Same slot cannot be booked twice
[x] Same Vapi retry does not duplicate appointment
[x] Unauthorized Vapi request returns 401
[x] Admin auth login works
[x] Appointment appears in admin appointment API
[x] Call summary is stored by backend
[x] Call log appears in admin call-log API without exposing raw summary/transcript
[x] Vapi tool audit redacts raw PII
```
