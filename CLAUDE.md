# CLAUDE.md - AI Hospital Voice Receptionist

Project rules for coding agents. Read before writing code.

Full spec lives in `docs/SYSTEM_PLAN.md`. Database details live in
`docs/DATABASE_SCHEMA.md`. Security risks live in
`docs/SECURITY_RISK_REGISTER.md`.

## Fixed Direction

- Build a single-hospital official system first, not SaaS.
- Test with Vapi Web Calls before attaching the hospital's real number.
- Use PostgreSQL as the source of truth.
- Keep Google Sheets out of the primary system; add it later only as export.
- Security target is production-lite: serious auth, PII protection, audit logs,
  and careful logging, without claiming full healthcare compliance yet.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic v2, python-dotenv
- DB: PostgreSQL
- Frontend: Next.js App Router, TypeScript, Tailwind, shadcn/ui
- Voice: Vapi API Request/custom tools

## Non-Negotiable Rules

1. Vapi endpoints must require `Authorization: Bearer <VAPI_TOOL_SECRET>`.
2. Never log raw names, phone numbers, appointment reasons, transcripts, or
   secrets.
3. Encrypt PII fields at rest and use phone hashes for lookup.
4. Appointment booking must use a database transaction and a unique constraint
   for doctor/date/time.
5. The assistant must not diagnose. It only routes to an appointment category
   and offers safe emergency/human handoff guidance.
6. Store all timestamps in UTC. Interpret schedules in `Asia/Karachi` unless
   the hospital config says otherwise.
7. Keep routers thin; business logic belongs in services.

## Build Order

1. Backend app skeleton, config, database connection
2. SQLAlchemy models and Alembic migrations
3. Seed hospital, departments, doctors, routing keywords, schedules
4. Vapi auth dependency and tool endpoints
5. Matching, availability, and booking services
6. End-of-call event storage
7. Tests for booking, auth, and safety behavior
8. Dashboard pages for appointments, doctors, schedules, and call logs

