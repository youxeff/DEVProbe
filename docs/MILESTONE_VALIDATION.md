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
