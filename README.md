# DevProbe

DevProbe is an AI-assisted code review and CI quality platform. It connects to GitHub, analyzes pull requests before merge, explains deterministic findings, and keeps a history of review risk.

Reviewers often have to piece together diffs, security warnings, missing test signals, and previous results. DevProbe brings them into one workflow: **repository → pull request → scan → findings and risk → review history**.

The implementation now covers Milestones 0–10. The core application, four real analyzer runners, database migrations, browser workflow, and Redis/Celery integration have been tested. **Live OpenAI, GitHub App, and Stripe activation, native container boot, and remote GitHub Actions execution remain external verification gates.** See the [validation ledger](docs/MILESTONE_VALIDATION.md), [original audit](docs/BUILD_AUDIT.md), and [end-to-end walkthrough](docs/WALKTHROUGH.md).

## Features

- Repository metadata, contributors, commits, open PR browsing, individual PR details, and changed files with nullable patches.
- Basic change heuristics plus Bandit, Radon, ESLint, and Semgrep CE adapters with one issue schema.
- Deterministic, uncapped risk scoring; severity/category charts; filtering by severity, category, file, and tool.
- SQL-backed scans, historical trends, failure metrics, AI token usage, and optional cost estimates.
- Optional structured OpenAI review; analyzer results remain usable if AI fails.
- Synchronous local mode or durable pending scans dispatched through Redis/Celery, with recovery and browser polling.
- GitHub App credentials, verified installation linking, signed/deduplicated PR webhooks, and updateable GitHub Checks.
- Password authentication, revocable sessions, organizations, invitation links, four roles, tenant ownership checks, quotas, and audit records.
- Optional Stripe-hosted checkout/portal, signed billing webhooks, and provider-derived plan changes.

## Screenshots

These are actual browser captures using the controlled test repository/provider fixtures; they are not claims about customer results.

![Scan result dashboard](docs/screenshots/scan-result.png)

![Organization settings](docs/screenshots/settings.png)

## Stack

| Layer | Implementation |
| --- | --- |
| Frontend | Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui source components, Recharts, SWR |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Storage | PostgreSQL for deployment; SQLite for the local quickstart and isolated unit tests |
| Jobs | Celery, Redis; one scan workflow shared by manual/API/webhook jobs |
| External APIs | GitHub REST and App OAuth, OpenAI Responses, optional Stripe |
| Quality | pytest, Ruff, Playwright, GitHub Actions, Docker Compose |

## Architecture

```mermaid
flowchart TD
    U[Developer] --> F[Next.js dashboard]
    F --> A[FastAPI and tenant authorization]
    H[Signed GitHub event] --> A
    A --> D[(PostgreSQL)]
    A --> Q[Redis queue]
    Q --> W[Celery worker]
    A --> S[Scan service]
    W --> S
    S --> G[GitHub service]
    S --> N[Analyzer coordinator]
    N --> T[Basic, Bandit, Radon, ESLint, Semgrep]
    T --> I[Canonical findings]
    I --> R[Deterministic risk]
    I --> L[Optional AI explanation]
    R --> D
    L --> D
    S --> C[Optional GitHub Check]
    D --> A
```

`POST /scans` returns a scan ID and status in either mode. The UI retrieves `/scans/{id}` and polls pending/running results. Redis carries only scan IDs. Workers load organization ownership from the persisted scan; broker messages cannot choose another tenant. The SQL pending row is durable even if queue dispatch fails.

## Local setup

Use Python 3.12 and Node.js 22 or newer. Run from this checkout, not a new starter project.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://localhost:3000**. The backend example enables the basic analyzer and local unauthenticated mode. Public repositories can be read without a token, subject to GitHub limits. To test accounts locally, set `AUTH_ENABLED=true` in `backend/.env`, keep `PUBLIC_URL=http://localhost:3000`, and restart the backend. Create an account in the browser.

To enable the additional analyzers:

```bash
cd backend
npm ci --prefix tools
python3.12 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
```

Then set `EXTERNAL_ANALYZERS=bandit,radon,eslint,semgrep`. Bandit and Radon are in the backend requirements; Semgrep has a separate Python environment. The process resource-limit implementation targets Linux/macOS; use Docker or WSL for Windows.

For PostgreSQL, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/devprobe` and run `alembic upgrade head`. Migration-managed SQL storage is always used by the application; the memory store remains only a test double. Do not run schema creation manually in production.

## Configuration

Copy the appropriate `.env.example`; never commit `.env`, PEM keys, tokens, or customer source.

| Variables | Purpose |
| --- | --- |
| `APP_ENV`, `AUTH_ENABLED`, `REGISTRATION_ENABLED` | Runtime mode and account controls. Production refuses to start without authentication, PostgreSQL, and an HTTPS `PUBLIC_URL`. |
| `PUBLIC_URL`, `SESSION_TTL_SECONDS` | Browser origin/callback URL and session lifetime; default 24 hours. Use the exact origin shown here in the browser. |
| `DATABASE_URL` | SQLAlchemy database URL. |
| `SCAN_MODE`, `REDIS_URL` | `sync` or `async`; broker URL for workers/scheduler. |
| `GITHUB_TOKEN` | Server-only PAT for **unscoped local development**. It never grants an authenticated organization access to private repositories. |
| `GITHUB_APP_ID`, `GITHUB_APP_SLUG`, `GITHUB_PRIVATE_KEY` | App identity and signing key. Escaped `\n` in PEM values is supported. |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_WEBHOOK_SECRET` | Installation verification OAuth and signed PR deliveries. |
| `EXTERNAL_ANALYZERS` | Comma-separated installed tools; empty runs basic analysis only. |
| `AI_ENABLED`, `OPENAI_API_KEY`, `OPENAI_MODEL` | Optional AI review, disabled by default. Model defaults to `gpt-4.1-mini`. |
| `AI_INPUT_PRICE_PER_MILLION`, `AI_OUTPUT_PRICE_PER_MILLION` | Optional verified current rates. Unset rates produce unknown cost, not an invented zero. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID` | Optional hosted billing; configure Stripe test mode before live mode. |
| `API_INTERNAL_URL` | Next.js **build-time** backend target; defaults to `http://127.0.0.1:8000`, Docker uses `http://backend:8000`. |

Full connection instructions are in [WALKTHROUGH.md](docs/WALKTHROUGH.md).

## Backend structure

| Directory | Responsibility |
| --- | --- |
| `app/main.py` | App creation, routers, middleware registration |
| `app/api/` | HTTP parsing/serialization and service calls |
| `app/schemas/` | Typed API contracts and canonical issues |
| `app/services/` | GitHub transport, scan orchestration, analyzers, scoring, AI, accounts, usage, integrations |
| `app/analyzers/` | Tool runners/parsers, fixed configuration, process limits |
| `app/models/`, `app/db/`, `migrations/` | SQL models, sessions, scan snapshots, schema migrations |
| `app/workers/` | Celery task entry points; no duplicate scanner |
| `tests/`, `scripts/` | Unit/API/database/provider tests and integration checks |

Frontend HTTP calls are centralized in `frontend/lib/api.ts`; UI types describe API responses, not ORM models.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health`, `/health/ready` | Liveness and database readiness |
| POST | `/repositories/parse-url`, `/repositories/metadata`, `/repositories/commits` | Parse, connect, retrieve commits |
| GET | `/repositories`, `/repositories/{id}`, `/repositories/{id}/scans` | Organization-scoped repositories/history |
| POST | `/pull-requests`, `/pull-requests/{number}`, `/pull-requests/{number}/files` | PR list/detail/files by `repo_url` |
| POST / GET | `/scans`, `/scans/{id}` | Submit and retrieve a scan |
| GET | `/scans?offset=0&limit=25`, `/analytics` | History and aggregate trends; optional `repository_id` |
| GET / POST | `/auth/session`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/password` | Account/session lifecycle |
| POST / GET | `/organizations`, `/organizations/members`, `/organizations/usage`, `/organizations/audit` | Organization creation and scoped administration |
| POST | `/organizations/invitations`, `/organizations/invitations/accept` | Generate/accept expiring invitation links |
| PATCH / DELETE | `/organizations/members/{id}` | Change role/remove access; retain at least one owner |
| GET / POST | `/github`, `/github/connect`, `/github/callback` | App status and OAuth ownership verification |
| PATCH / DELETE | `/github/installations/{id}` | Check publication preference/disconnection |
| POST | `/github/scans/{id}/check`, `/webhooks/github` | Publish/update a Check; receive signed events |
| GET / POST | `/billing`, `/billing/checkout`, `/billing/portal`, `/webhooks/stripe` | Billing status, hosted sessions, signed reconciliation |

FastAPI OpenAPI remains the authoritative method/schema list. Legacy `/analyze`, `/parse-repo-url`, `/repo/...`, and `/repositories/repo/...` aliases remain available and enforce the same authorization as canonical routes. See [API compatibility notes](docs/API_CHANGES.md).

With authentication enabled, requests need the session cookie; organization selection uses `X-Organization-ID` and verifies membership. Mutating requests also need the configured `Origin` and `X-CSRF-Token` matching the session's CSRF cookie. The frontend sends them automatically.

## Data model

Organizations own repositories, memberships, usage counters, audit events, and billing state. Repositories own PRs and scans; scans own issues and an optional structured AI review. Unique repository scope/GitHub-ID and repository/PR-number constraints retain identity. Deleting a repository through an administrative database operation cascades its PRs/scans/findings; no public destructive repository endpoint is provided.

Legacy rows with `organization_id=NULL` stay in local mode. Enabling authentication does **not** assign those rows to the first user. Organizations cannot read them. Connect and scan repositories inside the intended organization to build its history. Ownership is enforced in application queries; PostgreSQL row-level security is not configured.

## Analysis and risk scoring

The basic analyzer reads added patch lines and identifies large changes, TODO/FIXME, debug output, sensitive keywords, and code changes without added/updated test lines. Files changing more than 250 lines get the large-file warning. These are heuristics, not confirmed vulnerabilities or measured coverage.

External tools read bounded files at the PR's immutable head SHA. Bandit/ESLint/Semgrep findings are filtered to added lines. Radon reports complexity in changed files, not complexity delta. Missing patches, generated files, size limits, and unavailable tools produce visible limitations. A failing tool does not erase other results.

| Signal | Points |
| --- | ---: |
| Security critical / high / medium / low / info | 15 / 10 / 6 / 3 / 0 |
| Complexity high / medium | 5 / 3 |
| Non-informational style finding | 2 |
| Missing-test warning | 4 |
| Large file change | 2 |
| More than 15 changed files | 10 |
| 501–1000 changed lines | 10 |
| More than 1000 changed lines | 20 **instead of** 10 |

Risk levels: **Low 0–20; Medium 21–50; High 51–80; Critical 81+**. The score is uncapped and versioned. Size findings do not double-count their PR penalties. A low score does not prove safety.

## AI review

AI receives bounded normalized findings and metrics, never entire source files, patches, secrets, or PR prose. It explains findings using a strict JSON schema. Maximum input is 20,000 characters / 50 findings / 30 paths; maximum output is 1,200 tokens. Model/token usage and configured cost estimates are stored. Provider failures leave deterministic scan results completed and usable. [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Security and privacy

- Argon2id passwords; random opaque, hashed, expiring sessions; HttpOnly cookies; Secure cookies on HTTPS; origin and session-bound CSRF checks; database-backed login throttles.
- Membership and role validation on organization access; scoped scans/repositories/analytics/settings; viewer read-only behavior; owners control billing; admin/owner roles manage invitations/integrations.
- Free plan: 50 accepted scans/month, 5 repositories, 3 members. Pro: 1,000 scans/month, 50 repositories, 25 members. Atomic admission prevents concurrent quota overruns. Billing webhooks fetch current Stripe state rather than trusting a client plan or stale event.
- Source and full patches are transient; persisted findings omit matched literals. Fixed analyzer configuration, secret-free subprocess environments, deadlines, CPU/output/file bounds, temporary cleanup. No repository tests, hooks, installs, builds, or plugins are executed.
- Structured request logs omit query strings, bodies, headers, and exception payloads. The recommended Uvicorn command disables access logging so OAuth codes do not enter URL logs.
- These controls are **not a complete hostile-code sandbox**. Dedicated ephemeral OS isolation, egress restrictions, exact image/license review, backups, and operational hardening remain deployment work. Coverage execution is deferred until that isolation exists. See [SECURITY.md](docs/SECURITY.md) and [license review](docs/LICENSE_REVIEW.md).

## Tests and CI

```bash
cd backend
ruff check app tests scripts
pytest -q
# Dedicated PostgreSQL test database only:
POSTGRES_TEST_URL=postgresql+psycopg://USER:PASSWORD@HOST/devprobe_test python scripts/verify_postgresql.py
# With redis-server installed:
python scripts/verify_queue.py
```

```bash
cd frontend
npm run lint
npm run type-check
API_INTERNAL_URL=http://127.0.0.1:8100 npm run build
npx playwright install chromium
npm test
E2E_AUTH=true npm test
```

Browser tests start fixture-provider Uvicorn and the real frontend automatically. They use separate local databases, real routes, SQL persistence, deterministic scoring, and structured AI fixtures. They do not consume live API quotas or execute customer code. GitHub Actions defines the same checks plus native PostgreSQL and Compose build/boot gates. Actual outcomes and environment limitations are recorded in the validation ledger.

## Docker

```bash
cp .env.example .env
# Set a generated URL-safe POSTGRES_PASSWORD in .env.
docker compose config --quiet
docker compose up --build
```

Open `http://localhost:3000` and create your account. Compose includes frontend, API, migration job, worker, scheduler, PostgreSQL, and Redis. Ports bind to loopback. Database/Redis data use volumes. Application services run without root capabilities, with resource limits and read-only filesystems. `docker compose down` stops the stack; adding `--volumes` deletes its data.

Compose syntax was validated here. This workspace had no Docker daemon, so image build/boot is an explicit remaining verification gate; do not treat configuration validation as a deployment test.

## Roadmap and demo

Code is implemented through Milestone 10. Next deployment work is to run remote CI/container gates, configure and test real provider accounts, host behind HTTPS with isolated analysis workers, finish image/license review, and define backups/retention. Email delivery/verification, account recovery, enterprise SSO, custom rules, Kubernetes, and coverage execution are not included in this foundation.

There is no hosted demo URL yet. Run the local demo above and follow [the walkthrough](docs/WALKTHROUGH.md). The initial real public PR smoke test is recorded in [VALIDATION.md](docs/VALIDATION.md); fixture counts/screenshots are explicitly labeled and are not customer adoption metrics.
