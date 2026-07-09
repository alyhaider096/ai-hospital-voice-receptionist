# Security Risk Register

Security target for v1: production-lite. The system should be careful enough
for official internal testing and client review, but it must not claim full
healthcare compliance until the client requirements, contracts, hosting, and
retention policies are finalized.

## Risk Matrix

| ID | Risk | Severity | Default Fix |
|---|---|---:|---|
| R1 | Unauthorized Vapi tool call books fake appointments | High | Bearer auth on all `/vapi/*` endpoints; rotate secret before real use |
| R2 | Double booking the same doctor/date/time | High | DB transaction plus partial unique index on active appointments |
| R3 | Raw patient PII appears in logs | High | Redaction filter; never log request bodies for PII endpoints |
| R4 | Stored names/phones/reasons exposed if DB leaks | High | Encrypt PII at rest; use phone hashes for lookup |
| R5 | Assistant gives medical diagnosis | High | Prompt guardrails; routing-only API; emergency keyword handling |
| R6 | Emergency symptoms are treated as normal booking | High | Emergency routing keywords return safety note instead of doctor booking |
| R7 | Vapi tunnel URL changes and tools break | Medium | Keep Vapi setup docs updated; use production URL before real use |
| R8 | Tool retry creates duplicate appointment | High | Idempotency key based on call/patient/doctor/date/time |
| R9 | Admin account takeover | High | Strong password hashing; HttpOnly cookies; role-based access |
| R10 | Staff edits appointment without trace | Medium | Audit logs for all appointment and schedule changes |
| R11 | Full transcripts stored without consent | High | Default summary-only retention; explicit consent for transcripts/recordings |
| R12 | Dashboard exposes sensitive data to wrong role | High | Role-based access; mask PII by default |
| R13 | Timezone bug books wrong time | Medium | Store timestamps UTC; interpret schedules in hospital timezone |
| R14 | Public repo leaks system secrets | High | Private repo first; `.env` ignored; `.env.example` only |
| R15 | Backend stack trace leaks to Vapi/patient | Medium | Clean JSON errors and generic assistant-facing messages |

## Security Defaults

### API Authentication

- `/vapi/tools/*` requires `Authorization: Bearer <VAPI_TOOL_SECRET>`.
- `/vapi/events/*` requires the same Vapi secret.
- Admin APIs require authenticated dashboard session.

### PII Protection

Encrypt:

```txt
patients.full_name_encrypted
patients.phone_encrypted
appointments.reason_encrypted
call_logs.summary_encrypted
call_logs.transcript_encrypted
```

Hash:

```txt
patients.phone_hash
```

Never log:

```txt
patient name
phone
appointment reason
call transcript
call summary
API secrets
database URL
admin password
```

### Appointment Safety

Booking must:

- Validate doctor is active.
- Validate date is not in the past.
- Validate requested slot exists in generated availability.
- Run in a database transaction.
- Rely on a database uniqueness rule to block race conditions.
- Return a clean "slot no longer available" error on conflict.

### Medical Safety

The assistant must say it is booking appointments, not diagnosing.

Emergency examples:

```txt
severe chest pain
difficulty breathing
heavy bleeding
loss of consciousness
stroke symptoms
seizure
serious injury
```

Emergency response:

```txt
This may need urgent care. Please contact emergency services or visit the
emergency department immediately.
```

### Logging

Use structured logs, but redact sensitive fields before writing.

Allowed:

```txt
request_id
route
status_code
latency_ms
tool_name
appointment_ref
doctor_id
```

Not allowed:

```txt
full request bodies
raw phone numbers
raw patient names
raw symptoms/reasons
transcripts
authorization headers
```

## Pre-Launch Security Checklist

```txt
Vapi secret rotated
Admin bootstrap password changed
PII encryption key generated and backed up securely
Database backups enabled
Dashboard served over HTTPS
Production CORS locked down
Debug mode disabled
Logs checked for PII
Double-booking race test passed
Emergency phrase test passed
Retention policy approved
```

