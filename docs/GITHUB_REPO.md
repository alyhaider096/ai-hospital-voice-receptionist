# GitHub Repository Details

## Repository

```txt
Name: ai-hospital-voice-receptionist
Visibility: Private first
Shape: Monorepo
Default branch: main
Integration branch: dev
Feature branch pattern: feature/<short-name>
```

Description:

```txt
AI-powered hospital voice receptionist using Vapi, FastAPI, PostgreSQL, and
Next.js to route patients, check doctor availability, book appointments, and
maintain official appointment/call records.
```

Recommended topics:

```txt
fastapi
postgresql
vapi
voice-ai
healthcare
appointment-booking
nextjs
sqlalchemy
alembic
```

## First Commit Scope

```txt
README.md
CLAUDE.md
.env.example
.gitignore
docker-compose.yml
backend/README.md
frontend/README.md
docs/SYSTEM_PLAN.md
docs/DATABASE_SCHEMA.md
docs/VAPI_SETUP.md
docs/SECURITY_RISK_REGISTER.md
docs/GITHUB_REPO.md
infra/.gitkeep
scripts/.gitkeep
```

## Branch Strategy

```txt
main
  Stable working version. Keep demo-safe and protected after GitHub setup.

dev
  Active integration branch. Backend/frontend feature work merges here first.

feature/*
  One feature per branch, for example:
  feature/backend-models
  feature/vapi-tools
  feature/admin-dashboard
```

## GitHub Setup Commands

Local initialization:

```bash
git init
git branch -M main
git add .
git commit -m "Initial official system plan and repo skeleton"
```

Create private remote with GitHub CLI:

```bash
gh repo create ai-hospital-voice-receptionist \
  --private \
  --description "AI-powered hospital voice receptionist using Vapi, FastAPI, PostgreSQL, and Next.js." \
  --source . \
  --remote origin \
  --push
```

Create `dev` branch:

```bash
git checkout -b dev
git push -u origin dev
git checkout main
```

## Recommended GitHub Settings

After the private repo exists:

```txt
Enable secret scanning
Enable Dependabot alerts
Protect main branch
Require PR before merge into main
Keep repo private until demo data and docs are sanitized
```

## Public Portfolio Later

If this becomes public for CV/portfolio:

```txt
Remove official hospital/client details
Use fake doctors and fake patients only
Use screenshots with synthetic data
Keep .env and tunnel URLs out of commits
Add a demo video link
Add a privacy/safety note to README
```

