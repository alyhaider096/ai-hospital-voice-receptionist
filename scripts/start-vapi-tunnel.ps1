param(
  [string]$BackendUrl = "http://127.0.0.1:8001",
  [string]$CloudflaredPath = "C:\Program Files (x86)\cloudflared\cloudflared.exe",
  [switch]$SkipToolTests,
  [switch]$TestTools
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "work\logs"
$envPath = Join-Path $repoRoot "backend\.env"
$errLog = Join-Path $logDir "cloudflared-vapi-current.err.log"
$outLog = Join-Path $logDir "cloudflared-vapi-current.out.log"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $CloudflaredPath)) {
  $command = Get-Command cloudflared -ErrorAction SilentlyContinue
  if (-not $command) {
    throw "cloudflared was not found. Install Cloudflare Tunnel or pass -CloudflaredPath."
  }
  $CloudflaredPath = $command.Source
}

$escapedBackendUrl = [regex]::Escape($BackendUrl)
$oldTunnels = Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "cloudflared" -and $_.CommandLine -match $escapedBackendUrl }

foreach ($oldTunnel in $oldTunnels) {
  Stop-Process -Id $oldTunnel.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

Remove-Item -LiteralPath $errLog, $outLog -Force -ErrorAction SilentlyContinue

$runner = "& '$CloudflaredPath' tunnel --protocol http2 --url '$BackendUrl' 1> '$outLog' 2> '$errLog'"
Start-Process `
  -FilePath "powershell.exe" `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $runner) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden | Out-Null

$publicUrl = $null
$deadline = (Get-Date).AddSeconds(30)

while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 1
  $log = ""
  if (Test-Path $errLog) {
    $log += Get-Content -Raw $errLog
  }
  if (Test-Path $outLog) {
    $log += Get-Content -Raw $outLog
  }

  $match = [regex]::Match($log, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
  if ($match.Success) {
    $publicUrl = $match.Value
    break
  }

  $runningTunnel = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "cloudflared" -and $_.CommandLine -match $escapedBackendUrl }
  if (-not $runningTunnel) {
    throw "cloudflared exited before creating a tunnel. Check $errLog"
  }
}

if (-not $publicUrl) {
  throw "Could not find a Cloudflare public URL in $errLog"
}

$publicHost = ([uri]$publicUrl).Host
$fallbackIp = $null

function Get-PublicResolverIp {
  param([string]$HostName)

  $deadline = (Get-Date).AddSeconds(60)

  while ((Get-Date) -lt $deadline) {
    try {
      $nslookup = nslookup $HostName 1.1.1.1 2>$null
    } catch {
      $nslookup = @()
    }

    $ipv4 = $nslookup |
      Select-String -Pattern "^\s*(\d{1,3}\.){3}\d{1,3}\s*$" |
      Select-Object -First 1

    if ($ipv4) {
      return $ipv4.Matches[0].Value.Trim()
    }

    Start-Sleep -Seconds 2
  }

  return $null
}

function Invoke-TunnelJson {
  param(
    [string]$Path,
    [string]$Method = "GET",
    [hashtable]$Headers = @{},
    [string]$Body = $null
  )

  $uri = "$publicUrl$Path"

  if (-not $script:fallbackIp) {
    $script:fallbackIp = Get-PublicResolverIp -HostName $publicHost
  }

  if (-not $script:fallbackIp) {
    throw "Public DNS did not resolve $publicHost"
  }

  $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
  if (-not $curl) {
    throw "curl.exe was not found. Cannot verify quick tunnel while local DNS is stale."
  }

  $args = @(
    "--resolve", "$publicHost`:443:$script:fallbackIp",
    $uri,
      "--max-time", "10",
    "--silent",
    "--show-error",
    "--fail"
  )

  if ($Method -eq "POST") {
    $bodyFile = Join-Path $logDir "vapi-tool-body-$([guid]::NewGuid()).json"
    Set-Content -LiteralPath $bodyFile -Value $Body -NoNewline -Encoding UTF8
    try {
      foreach ($header in $Headers.GetEnumerator()) {
        $args += @("-H", "$($header.Key): $($header.Value)")
      }
      $args += @("--data-binary", "@$bodyFile")
      $raw = & curl.exe @args
    } finally {
      Remove-Item -LiteralPath $bodyFile -Force -ErrorAction SilentlyContinue
    }
  } else {
    $raw = & curl.exe @args
  }

  if ($LASTEXITCODE -ne 0) {
    throw "curl tunnel check failed for $Path"
  }

  return $raw | ConvertFrom-Json
}

Write-Host ""
Write-Host "Vapi backend tunnel is ready:"
Write-Host $publicUrl
Write-Host ""
Write-Host "Paste these Request URLs into Vapi:"
Write-Host "$publicUrl/vapi/tools/lookup-caller-history"
Write-Host "$publicUrl/vapi/tools/classify-call-intent"
Write-Host "$publicUrl/vapi/tools/match-doctor"
Write-Host "$publicUrl/vapi/tools/check-availability"
Write-Host "$publicUrl/vapi/tools/book-appointment"
Write-Host "$publicUrl/vapi/events/end-of-call"
Write-Host ""

if ($SkipToolTests -or -not $TestTools) {
  Write-Host "Tool tests not run. Add -TestTools to run public endpoint smoke tests."
  return
}

if (-not (Test-Path $envPath)) {
  throw "backend\.env was not found. Cannot test authenticated Vapi tools."
}

$secret = (Get-Content $envPath |
  Where-Object { $_ -match "^VAPI_TOOL_SECRET=" } |
  Select-Object -First 1) -replace "^VAPI_TOOL_SECRET=", ""

if (-not $secret -or $secret -match "replace-with") {
  throw "VAPI_TOOL_SECRET is missing or still set to a placeholder."
}

$headers = @{
  Authorization = "Bearer $secret"
  "Content-Type" = "application/json"
}

$health = Invoke-TunnelJson -Path "/health"
if ($health.status -ne "ok") {
  throw "Public tunnel health check failed."
}

$classify = Invoke-TunnelJson `
  -Path "/vapi/tools/classify-call-intent" `
  -Method Post `
  -Headers $headers `
  -Body (@{ utterance = "I want to book an appointment for eye pain" } | ConvertTo-Json -Compress)

$matchDoctor = Invoke-TunnelJson `
  -Path "/vapi/tools/match-doctor" `
  -Method Post `
  -Headers $headers `
  -Body (@{ symptoms = "eye pain and blurry vision" } | ConvertTo-Json -Compress)

$availability = Invoke-TunnelJson `
  -Path "/vapi/tools/check-availability" `
  -Method Post `
  -Headers $headers `
  -Body (@{ doctor_id = $matchDoctor.doctor_id; date = "2026-07-15" } | ConvertTo-Json -Compress)

Write-Host "Smoke tests passed:"
Write-Host "health: ok"
Write-Host "classifyCallIntent: $($classify.intent)"
Write-Host "matchDoctorBySymptoms: $($matchDoctor.doctor_name) / $($matchDoctor.specialty)"
Write-Host "checkAvailability slots: $(@($availability.available_slots).Count)"
Write-Host ""
Write-Host "Do not print or paste the raw secret anywhere except the Vapi Authorization header/credential."
