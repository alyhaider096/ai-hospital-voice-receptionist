# Vapi Web Call Runbook

Use this runbook after the backend is running locally and before attaching the
hospital's official phone number.

## Current Backend URL

Local backend:

```txt
http://127.0.0.1:8001
```

Vapi needs a public HTTPS URL. For the fastest local test, run:

```powershell
.\scripts\start-vapi-tunnel.ps1
```

The script stops old hospital backend tunnels, starts one fresh Cloudflare
tunnel to `http://127.0.0.1:8001`, forces HTTP/2 transport, and prints the
exact Vapi request URLs.

To also run public endpoint smoke tests without printing the `VAPI_TOOL_SECRET`,
use:

```powershell
.\scripts\start-vapi-tunnel.ps1 -TestTools
```

Manual alternatives:

```bash
ngrok http 8001
```

or:

```bash
cloudflared tunnel --protocol http2 --url http://127.0.0.1:8001
```

Neither tunnel tool is committed to the repo. Install and authenticate the one
you choose on the local machine.

Important: free quick tunnels are temporary. If the agent says it cannot connect
to the appointment system, generate a fresh tunnel and replace every Vapi tool
Request URL with the new public URL.

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

Create these API Request tools first:

```txt
lookupCallerHistory
classifyCallIntent
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

## If Vapi Cannot Connect

Use this checklist in order:

```txt
1. Confirm backend health: http://127.0.0.1:8001/health returns {"status":"ok"}.
2. Run .\scripts\start-vapi-tunnel.ps1 to get a fresh public HTTPS URL.
3. Paste the new base URL into every Vapi API Request tool.
4. Keep method as POST for all hospital tools.
5. Keep Authorization as: Bearer <VAPI_TOOL_SECRET>.
6. Confirm request body field names match the docs exactly:
   symptoms, doctor_id, date, patient_name, phone, start_time, reason.
7. Save each tool and save/publish the assistant again.
8. Test matchDoctorBySymptoms first, then checkAvailability, then bookAppointment.
```

Do not use `localhost`, `127.0.0.1`, or an expired tunnel URL inside Vapi.
Vapi must reach the backend over the public internet.

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
