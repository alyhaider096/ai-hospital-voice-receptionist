param(
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$VapiSecret = "replace-with-long-random-vapi-secret",
  [string]$AdminEmail = "admin@example.com",
  [string]$AdminPassword = "change-this-password"
)

$ErrorActionPreference = "Stop"

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Get-NextOpenDate {
  $date = (Get-Date).AddDays(1)
  while ([int]$date.DayOfWeek -eq 0) {
    $date = $date.AddDays(1)
  }
  return $date.ToString("yyyy-MM-dd")
}

$vapiHeaders = @{ Authorization = "Bearer $VapiSecret" }
$results = [ordered]@{}

$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
Assert-True ($health.status -eq "ok") "Health check failed."
$results.health = "ok"

$match = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/tools/match-doctor" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body (@{ symptoms = "eye pain and blurry vision" } | ConvertTo-Json)
Assert-True ($match.specialty -eq "Ophthalmology") "Doctor matching failed."
$results.matchDoctorBySymptoms = "ok"

$emergency = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/tools/match-doctor" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body (@{ symptoms = "severe chest pain and difficulty breathing" } | ConvertTo-Json)
Assert-True ($null -eq $emergency.doctor_id) "Emergency case returned a normal doctor."
Assert-True ($emergency.safety_note -like "*emergency*") "Emergency safety note missing."
$results.emergencySafety = "ok"

$date = Get-NextOpenDate
$availability = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/tools/check-availability" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body (@{ doctor_id = $match.doctor_id; date = $date } | ConvertTo-Json)
Assert-True ($availability.available_slots.Count -gt 0) "No available slots returned."
$results.checkAvailability = "ok"

$slot = $availability.available_slots[0].start_time
$callId = "smoke-$([guid]::NewGuid().ToString())"
$bookingPayload = @{
  patient_name = "Smoke Test Patient"
  phone = "+923009998888"
  doctor_id = $match.doctor_id
  date = $date
  start_time = $slot
  reason = "eye pain"
  vapi_call_id = $callId
}

$booking = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/tools/book-appointment" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body ($bookingPayload | ConvertTo-Json)
Assert-True ($booking.status -eq "booked") "Booking failed."
Assert-True ($booking.appointment_ref -like "APT-*") "Appointment reference missing."
$results.bookAppointment = "ok"

$retry = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/tools/book-appointment" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body ($bookingPayload | ConvertTo-Json)
Assert-True ($retry.appointment_ref -eq $booking.appointment_ref) "Idempotent retry created a different appointment."
$results.idempotentRetry = "ok"

try {
  $doublePayload = $bookingPayload.Clone()
  $doublePayload.vapi_call_id = "smoke-double-$([guid]::NewGuid().ToString())"
  Invoke-RestMethod `
    -Uri "$BaseUrl/vapi/tools/book-appointment" `
    -Method Post `
    -Headers $vapiHeaders `
    -ContentType "application/json" `
    -Body ($doublePayload | ConvertTo-Json) | Out-Null
  throw "Double booking unexpectedly succeeded."
} catch {
  if ($_.Exception.Response.StatusCode.value__ -ne 422) {
    throw "Double booking returned unexpected status: $($_.Exception.Response.StatusCode.value__)"
  }
}
$results.doubleBooking = "rejected"

$callLogId = "smoke-call-log-$([guid]::NewGuid().ToString())"
$callLog = Invoke-RestMethod `
  -Uri "$BaseUrl/vapi/events/end-of-call" `
  -Method Post `
  -Headers $vapiHeaders `
  -ContentType "application/json" `
  -Body (@{
    vapi_call_id = $callLogId
    channel = "vapi_web"
    status = "ended"
    summary = "Smoke test summary"
    transcript = "Smoke test transcript"
  } | ConvertTo-Json)
Assert-True ($callLog.status -eq "saved") "End-of-call save failed."
$results.endOfCall = "ok"

$login = Invoke-RestMethod `
  -Uri "$BaseUrl/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json)
Assert-True (-not [string]::IsNullOrWhiteSpace($login.access_token)) "Admin login did not return a token."
$results.adminLogin = "ok"

$adminHeaders = @{ Authorization = "Bearer $($login.access_token)" }
$callLogs = Invoke-RestMethod -Uri "$BaseUrl/admin/call-logs" -Method Get -Headers $adminHeaders
$savedLog = $callLogs | Where-Object { $_.vapi_call_id -eq $callLogId } | Select-Object -First 1
Assert-True ($null -ne $savedLog) "Admin call log not found."
Assert-True ($savedLog.has_summary -and $savedLog.has_transcript) "Admin call log privacy flags missing."
Assert-True (-not ($savedLog.PSObject.Properties.Name -contains "summary")) "Raw summary leaked in admin call logs."
Assert-True (-not ($savedLog.PSObject.Properties.Name -contains "transcript")) "Raw transcript leaked in admin call logs."
$results.adminCallLogs = "ok"

[pscustomobject]$results
