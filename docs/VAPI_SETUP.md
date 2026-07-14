# Vapi Setup

This system is tested first with Vapi Web Calls. The hospital's official phone
number should be attached only after the backend, database, dashboard, and tool
calls are verified.

## Assistant Purpose

The assistant is a hospital voice receptionist. It can:

- Greet patients
- Ask what appointment they need
- Collect symptoms for routing only
- Collect patient name and phone
- Check doctor availability
- Book a confirmed appointment
- Provide appointment reference
- Save a call summary

The assistant must not:

- Diagnose medical conditions
- Give treatment advice
- Promise emergency care over the phone
- Book without explicit confirmation
- Expose internal API errors to the patient

## Tool URLs

During local testing, expose the FastAPI backend. The backend usually runs on
`8001` in this workspace because `8000` may already be occupied:

```bash
ngrok http 8001
```

Use the tunnel URL:

```txt
https://your-tunnel-url/vapi/tools/match-doctor
https://your-tunnel-url/vapi/tools/check-availability
https://your-tunnel-url/vapi/tools/book-appointment
https://your-tunnel-url/vapi/events/end-of-call
```

Final production URLs should replace the tunnel URL after deployment.

For the exact dashboard tool definitions, use
`docs/vapi-tools.template.json`. For the step-by-step Web Call test flow, use
`docs/VAPI_WEB_CALL_RUNBOOK.md`.

## Authentication

All Vapi tool requests must include:

```txt
Authorization: Bearer <VAPI_TOOL_SECRET>
```

Recommended Vapi setup:

1. Create a secret in Vapi custom credentials.
2. Attach that credential to each tool.
3. Do not paste secrets into descriptions or prompts.
4. Rotate the secret before real hospital use.

## Tool Definitions

### Tool 1: `matchDoctorBySymptoms`

Method:

```txt
POST
```

Path:

```txt
/vapi/tools/match-doctor
```

Description:

```txt
Match the patient's described symptoms to the most appropriate doctor or
department for appointment routing only. This tool must not diagnose.
```

Input schema:

```json
{
  "type": "object",
  "properties": {
    "symptoms": {
      "type": "string",
      "description": "The patient's symptoms in their own words."
    }
  },
  "required": ["symptoms"]
}
```

### Tool 2: `checkAvailability`

Method:

```txt
POST
```

Path:

```txt
/vapi/tools/check-availability
```

Description:

```txt
Check available appointment slots for a doctor on a requested date. If no
standard slot is available, use the returned next_available_dates and
handoff_recommended fields to guide the caller.
```

Input schema:

```json
{
  "type": "object",
  "properties": {
    "doctor_id": {
      "type": "string",
      "description": "Doctor UUID returned by matchDoctorBySymptoms."
    },
    "date": {
      "type": "string",
      "description": "Requested appointment date in YYYY-MM-DD format."
    }
  },
  "required": ["doctor_id", "date"]
}
```

Important response fields:

```txt
message               -> plain spoken availability result; use this first
available_slots       -> slots for the requested date
next_available_dates -> nearest future dates when requested date has no slots
next_available_summary -> plain text summary of next available dates
requested_date_was_past -> true if Vapi sent an old relative date
earliest_available_date -> first future date available
earliest_available_start_time -> first future time in HH:mm
earliest_available_display_time -> first future time for speech
handoff_recommended  -> true when no slot is available for today/tomorrow
safe_handoff_note    -> receptionist handoff instruction for urgent no-slot calls
```

### Tool 3: `bookAppointment`

Method:

```txt
POST
```

Path:

```txt
/vapi/tools/book-appointment
```

Description:

```txt
Book an appointment after the patient explicitly confirms the doctor, date,
and time.
```

Input schema:

```json
{
  "type": "object",
  "properties": {
    "patient_name": {
      "type": "string"
    },
    "phone": {
      "type": "string"
    },
    "doctor_id": {
      "type": "string"
    },
    "date": {
      "type": "string",
      "description": "Appointment date in YYYY-MM-DD format."
    },
    "start_time": {
      "type": "string",
      "description": "Appointment start time in HH:mm 24-hour format."
    },
    "reason": {
      "type": "string"
    },
    "vapi_call_id": {
      "type": "string"
    }
  },
  "required": ["patient_name", "phone", "doctor_id", "date", "start_time", "reason"]
}
```

Important response fields:

```txt
status                 -> booked
appointment_ref        -> official reference, for dashboard/system use
appointment_ref_spoken -> speech-friendly reference; read this to the caller
message                -> confirmation message
```

## Assistant Prompt Draft

```txt
You are the hospital's AI voice receptionist. Your job is to help patients book
appointments safely and politely.

You may ask for symptoms only to route the patient to the right department or
doctor. You must not diagnose, prescribe medicine, or provide treatment advice.

If the patient mentions severe chest pain, difficulty breathing, heavy bleeding,
loss of consciousness, stroke symptoms, or any urgent emergency, tell them to
contact emergency services or visit the emergency department immediately.

For normal appointment booking:
1. Ask what problem or symptoms they want an appointment for.
2. Use matchDoctorBySymptoms.
3. Ask for preferred date if not already provided.
4. Use checkAvailability.
5. Offer up to three available slots.
6. Ask for patient name and phone number.
7. Repeat doctor, date, and time for confirmation.
8. Only after the patient confirms, use bookAppointment.
9. Read appointment_ref_spoken clearly to the caller.

If checkAvailability returns no available_slots:
1. First read and follow the returned message field.
2. If earliest_available_date and earliest_available_display_time are present,
   offer that option.
3. If handoff_recommended is true, say: "I do not see a standard slot for that
   date. Since this sounds urgent, I can connect you with a human receptionist
   for assistance."
4. Do not imply the patient is safe to wait.
5. Do not diagnose or provide treatment instructions.

If a tool returns an error, apologize briefly and offer another slot or human
receptionist support. Do not read raw technical errors to the patient.
```

## Web Call Test Script

1. Start backend locally.
2. Start ngrok/cloudflared tunnel.
3. Configure Vapi tools with tunnel URLs.
4. Start Vapi Web Call.
5. Say: "I have eye pain and blurry vision. I want an appointment tomorrow."
6. Confirm one offered slot.
7. Confirm name and phone.
8. Verify appointment appears in database/dashboard.
9. Verify call summary appears in call logs.
10. Try booking the same slot again and expect a slot-unavailable response.

## Before Official Number Attachment

Checklist:

```txt
Backend deployed behind HTTPS
Vapi tool URLs updated from tunnel to production domain
Vapi tool secret rotated
Dashboard login enabled
Database backups enabled
Emergency guidance tested
Double-booking test passed
Call summary retention decision documented
Hospital has approved greeting and consent line
```
