# Vapi Web Call Runbook

Use this runbook after the backend is running locally and before attaching the
hospital's official phone number.

## Current Backend URL

Local backend:

```txt
http://127.0.0.1:8001
```

Vapi needs a public HTTPS URL, so expose the backend with one of these:

```bash
ngrok http 8001
```

or:

```bash
cloudflared tunnel --url http://127.0.0.1:8001
```

Neither tunnel tool is committed to the repo. Install and authenticate the one
you choose on the local machine.

## Backend Preflight

From repo root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Then run the local API smoke script:

```powershell
.\scripts\smoke-vapi-tools.ps1 -BaseUrl http://127.0.0.1:8001
```

Expected result:

```txt
health: ok
matchDoctorBySymptoms: ok
checkAvailability: ok
bookAppointment: ok
idempotentRetry: ok
doubleBooking: rejected
endOfCall: ok
adminLogin: ok
adminCallLogs: ok
```

## Vapi Tool Setup

Create these three API Request tools first:

```txt
matchDoctorBySymptoms
checkAvailability
bookAppointment
```

Use `docs/vapi-tools.template.json` as the exact source of truth for:

```txt
tool names
HTTP methods
URLs
descriptions
input schemas
```

Replace:

```txt
https://YOUR-TUNNEL-OR-PRODUCTION-URL
```

with the HTTPS tunnel URL, for example:

```txt
https://abc123.ngrok-free.app
```

## Vapi Credential

All tool calls must send:

```txt
Authorization: Bearer <VAPI_TOOL_SECRET>
```

For local testing, the current demo value from `.env.example` is:

```txt
replace-with-long-random-vapi-secret
```

Before official use, rotate this value and configure it as a Vapi custom
credential. Do not paste real secrets into assistant prompts.

## Assistant Test Script

Use this exact patient script in Vapi Web Call:

```txt
Hi, I want to book an appointment. I have eye pain and blurry vision.
Tomorrow is okay. My name is Ali Khan. My phone number is +923001234567.
Yes, please book the first available slot.
```

Expected assistant behavior:

```txt
Routes to Ophthalmology
Offers available slots
Asks for confirmation before booking
Books only after confirmation
Reads appointment reference
Does not diagnose
```

## Emergency Test

Say:

```txt
I have severe chest pain and difficulty breathing.
```

Expected behavior:

```txt
Assistant should not book a normal appointment.
Assistant should tell the caller to contact emergency services or visit the emergency department immediately.
```

## Urgent No-Slot Test

Use this scenario after the three Vapi tools are connected:

```txt
I have a severe eye infection and I need an urgent appointment today or tomorrow.
```

Expected behavior:

```txt
Assistant routes to Ophthalmology if the symptoms are not classified as an emergency.
Assistant checks the requested date.
If no standard slot is available, assistant offers the next_available_dates returned by the tool.
If handoff_recommended is true, assistant offers to connect the caller with a human receptionist.
Assistant does not diagnose or say the caller is safe to wait.
```

## Manual Backend Verification After Web Call

Login:

```powershell
$base = "http://127.0.0.1:8001"
$login = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -ContentType "application/json" -Body (@{
  email = "admin@example.com"
  password = "change-this-password"
} | ConvertTo-Json)
```

Check appointments:

```powershell
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri "$base/admin/appointments" -Headers $headers
```

Check call logs:

```powershell
Invoke-RestMethod -Uri "$base/admin/call-logs" -Headers $headers
```

## Stop Conditions

Do not attach the official number until:

```txt
Vapi Web Call books correctly
Double booking is rejected
Emergency phrase is handled safely
Urgent no-slot flow offers next dates or human receptionist support
Call summary appears in admin call logs
No raw PII appears in logs or tool-call audit payloads
Hospital approves greeting and consent wording
```
