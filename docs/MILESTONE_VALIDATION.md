# Milestone validation ledger

This file records work after the original M0/M1 validation in `VALIDATION.md`.

## M2 — persistence (2026-09-21)

- 146 backend tests passed, including the original 139 checks.
- Alembic clean upgrade, downgrade, re-upgrade, and schema-drift checks passed.
- Repository/PR identity, scan/issue persistence, atomic claim, unique PR
  constraint, and foreign-key cascades passed.
- PostgreSQL dialect tested over psycopg against PGlite 0.5.8 (PostgreSQL 18.3
  compiled to WebAssembly): clean migration, no schema drift, scan creation,
  atomic claim, issue persistence, and reading through a new connection passed.
- PGlite is a test runtime, not the production database. Native PostgreSQL and
  Compose deployment require a host that can run those services. This workspace
  cannot install system packages or run a system database daemon.
- MemoryScanStore is retained as a unit-test double; the application uses SQL.

## Publishing access

The user approved pushing all work and opening a draft PR. Direct Git has no
write credential; the connected GitHub integration returns HTTP 403
`Resource not accessible by integration` for creating a Git tree. No remote
branch/PR has been created. Local milestone commits retain the work.

## M3 — browser MVP

- Production Next.js build, TypeScript checks, and ESLint passed.
- Chromium browser tests passed for the complete repository → PR → SQL-backed
  scan → issue filter → reload → history flow, invalid URL/not-found states,
  and mobile navigation/layout. GitHub responses were fixtures; the backend,
  database, scoring, and UI were real.
- The constrained workspace uses a separate Chromium launch per test because
  its single-process browser exits between contexts. Normal CI uses Playwright's
  standard browser. The screenshot is actual fixture test output, not product usage.
- Added POST /pull-requests/{number}, an additive detail endpoint supporting closed PRs.

## M4 — external static analyzers

- Bandit 1.9.4, Radon 6.0.1, ESLint 9.39.5 with the TypeScript parser,
  and Semgrep OSS 1.177.0 each passed an actual executable fixture test,
  in that implementation order. The full backend suite passed 161 tests.
- Verified timeouts, secret-free subprocess environment, ignoring customer
  ESLint configuration, pinned source reads, unsafe path rejection, canonical
  results, and retaining other findings when an analyzer fails.
- At most 50 source files, 1 MB per file, 5 MB total; generated/build files
  skipped. Tool output is bounded, discarded, and never logged. Source files
  have generated local names and are deleted with the temporary workspace.
- Bandit/ESLint/Semgrep findings are filtered to added lines. Radon reports
  complexity in the changed files (including existing functions); it is not
  a base-versus-head complexity delta.
- Safe subprocess execution is not a hostile-code sandbox. No repository code,
  package hooks, or tests are executed. Hosted deployment still needs OS/container
  isolation and egress controls for parser vulnerabilities.
- CLI behavior follows the official [Bandit](https://bandit.readthedocs.io/en/latest/man/bandit.html),
  [Radon](https://radon.readthedocs.io/en/latest/commandline.html),
  [ESLint](https://eslint.org/docs/latest/use/command-line-interface), and
  [Semgrep](https://docs.semgrep.dev/cli-reference) documentation.

## M5 — AI-assisted review

- 166 backend tests passed. Structured output, invalid/refused output handling,
  bounded input, provider failure isolation, persistence, usage and configured
  cost calculations tested. AI output rendering passed the Chromium journey.
- Uses the [OpenAI Responses structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs).
  Sends normalized findings and metrics only: no patches, PR descriptions,
  complete source, credentials, or tool access. AI cannot publish to GitHub.
- Max 50 findings, 30 filenames, 20,000 input characters, 1,200 output tokens,
  30-second timeout; provider response storage disabled. No automatic retries.
- Enabled only with AI_ENABLED=true and OPENAI_API_KEY. No key is configured in
  this workspace: provider and token accounting checks used test responses.
  Estimated cost stays null until per-million rates are configured explicitly.

## M6 — history and analytics

- 168 backend tests passed. Aggregate totals, completed-only risk/duration
  averages, failure rate, distinct PR count, category/severity counts, pagination,
  and honest empty states verified.
- Frontend lint, TypeScript, production build, and browser journey through
  scan history/trends passed. Charts show the latest 30 completed scans;
  workspace totals include the complete matching dataset.

## M7 — background scans

- 170 backend tests passed. Async creation returns pending, duplicate delivery
  is claimed once, and lost dispatches remain durable in SQL for recovery.
- Ran actual Redis 6.2.14, a separate Celery 5.6.3 worker, and Uvicorn: POST
  returned pending; the worker completed a persisted scan with 4 findings and
  risk 16. Re-delivery did not rerun it. Providers used deterministic fixtures.
- Browser test verified pending → running → completed polling. It caught and
  fixed polling initialization before initial data arrived.
- Celery Beat retries pending dispatches; stale running scans fail after the
  worker execution window. They require a new scan instead of replaying AI
  charges automatically. Queue contains only scan IDs, not customer source.

## M8 — containers and CI

- Added separate backend/frontend images, worker and recovery scheduler services,
  PostgreSQL/Redis volumes, readiness checks, migration-first startup, non-root
  application users, read-only app filesystems, resource limits, and local-only ports.
- Official Docker Compose 2.39.4 `config --quiet` passed. CI YAML parsed.
- PostgreSQL protocol validation reran all migrations through the queue revision:
  no schema drift; JSONB, claim, reconnect persistence and cascade checks passed
  against the PGlite PostgreSQL runtime. Readiness tests passed.
- CI defines backend lint/tests, a native PostgreSQL check, real queue test,
  frontend lint/types/build/browser tests, image builds and a complete stack boot.
- This workspace has no Docker daemon. Images and the complete Compose stack
  have NOT been boot-tested here. CI has NOT run remotely because publishing
  remains blocked by GitHub write access. These are explicit remaining gates.

## Milestone 9 — GitHub App integration

- Added short-lived RS256 App JWTs and in-memory installation-token caching. Installation association requires a GitHub OAuth user who owns the account or is an active organization administrator. A remote installation cannot be reassigned across DevProbe organizations.
- Added raw-body HMAC verification, bounded webhook bodies, durable pending scans, unique delivery/commit deduplication, and stale-head rejection. Webhooks always enqueue; the worker runs the same scan service. Revoked/suspended installations stop authorizing new scans.
- Added GitHub Checks with one local record per repository/commit and remote `external_id` recovery. Repeated scans update the existing check. Output consists of application-owned metrics; source text and AI instructions cannot control posting. Automatic publication is opt-in per installation.
- Validation: **182 backend tests passed** including JWT verification, token caching, signature rejection, duplicate deliveries, revocation, stale commits, ownership denial, and check reuse. Ruff passed; clean SQLite migrations upgrade/downgrade/re-upgrade and schema comparison passed.
- GitHub App/OAuth transport is mocked in automated tests. Live installation, webhook delivery, and Check publication require configured App credentials and a reachable HTTPS callback. No real PR comments or Checks were posted. Authenticated connection/settings UI is added in Milestone 10.

## Milestone 10 — SaaS foundation

- Added Argon2id account credentials; opaque hashed/expiring/revocable sessions; session-bound CSRF and Origin checks; SQL-backed throttling; production configuration guards and input-redacted configuration errors.
- Added organizations, memberships, expiring invitation links, owner/admin/member/viewer roles, last-owner protection, tenant-scoped repository/scan/history/analytics/settings reads, and isolation of legacy unowned data. Users who lose all memberships cannot fall back into local-mode data and can create a new organization.
- Added transactional scan/repository/member quotas, monthly usage counters, safe audit events, and structured request logs. Queue workers load the persisted tenant; they never receive a tenant choice in the job payload.
- Added authenticated GitHub App connection settings with one-time user-bound OAuth state and PKCE, owner/admin verification, scoped disconnection, and explicit/opt-in Check output.
- Added optional Stripe-hosted checkout and customer portal. Signed webhooks deduplicate and reconcile current provider state; client-supplied plan/price fields do not grant entitlement. Repeated checkout requests reuse an open session. Tests exercised the actual Stripe SDK webhook parser and mocked provider transport. No live charges were attempted.
- Added login/registration, organization selector, invitation acceptance, members/roles, usage, audit, GitHub connection, billing, password-change, and Check publication UI. Screenshots were captured and visually inspected; mobile settings overflow was tested.
- Validation: **194 backend tests passed**; Ruff passed. Frontend lint, TypeScript check, and production build passed. Browser tests passed for the complete repository/PR/scan/history flow, errors, mobile navigation, pending/running polling, and authenticated registration/scan/settings/tenant-isolation/logout.
- The real Redis + separate Celery + Uvicorn integration was rerun with authentication enabled: pending → tenant-owned completed scan; duplicate delivery preserved the result. Latest migrations passed against PGlite's PostgreSQL wire protocol/JSONB implementation and clean SQLite upgrade/downgrade/re-upgrade. This is not a claim of native PostgreSQL or Docker daemon testing.

## Final verification summary — 2026-09-21

| Gate | Observed result |
| --- | --- |
| Backend regression suite | 194 passed; one non-failing Starlette/httpx TestClient deprecation warning |
| Ruff; frontend ESLint; TypeScript | Passed |
| Next.js production build | Passed; all product/account routes built |
| Chromium browser workflows | 5 passed (four local-workspace cases plus one authenticated case); run separately because this workspace uses a single-process Chromium build |
| Actual static analyzer executables | Bandit, Radon, ESLint, Semgrep fixture tests passed |
| Authenticated queue workflow | Passed with real Redis and a separate Celery process |
| SQL migration/persistence tests | Clean SQLite cycle passed; PostgreSQL protocol/JSONB/claim/reconnect/cascade check passed through PGlite |
| Compose configuration | Passed `docker compose config --quiet` with non-secret validation input |
| Native Docker build/boot and PostgreSQL 16 | Not run: no Docker daemon/native service in this workspace; CI jobs provided |
| Remote GitHub Actions | Not run: current GitHub connection denies writes |
| Live public GitHub | Earlier successful `psf/requests#7616` scan recorded in `VALIDATION.md`. The final 2026-09-21 retry could not reach GitHub and correctly returned safe HTTP 503 with a persisted failed scan ID. No fresh successful live scan is claimed. |
| Live OpenAI / GitHub App / Stripe | Not activated: provider credentials absent; contract/error/security paths tested with controlled transport |
| Commercial release clearance | Not claimed; dependency inventory/review provided, exact images/hosted terms and operational controls still need release review |

Current branch: `codex/devprobe-scan-foundation`. Changes are committed locally. Git push lacks a usable write credential; the connected GitHub write API returned `403 Resource not accessible by integration`. No remote branch, PR, merge, hosted demo, or deployment is claimed. A complete patch is provided for review/import without changing the user's main branch.
