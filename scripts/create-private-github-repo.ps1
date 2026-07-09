param(
  [string]$RepoName = "ai-hospital-voice-receptionist",
  [string]$Description = "AI-powered hospital voice receptionist using Vapi, FastAPI, PostgreSQL, and Next.js."
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Write-Error "GitHub CLI is not installed. Install it from https://cli.github.com/ and run: gh auth login"
}

gh auth status

gh repo create $RepoName `
  --private `
  --description $Description `
  --source . `
  --remote origin `
  --push

git push -u origin main

if (-not (git branch --list dev)) {
  git branch dev
}

git push -u origin dev

Write-Host "Private GitHub repo created and pushed: $RepoName"

