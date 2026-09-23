# Backend audit and implementation plan

Baseline: `ad8b4ca3777654ad348a71af55a7670f9706e8be` (main), 2026-09-19.

## What actually exists

`backend/app/` already contains `api/`, `core/`, `db/`, `schemas/`, and
`services/`. `main.py` is already small. `frontend/` is an unmodified Next.js
App Router starter, with no DevProbe UI or API integration.

Starting `uvicorn app.main:app` fails: `api/scans.py` imports the nonexistent
`scan_service.create_scan_result`. The empty `api/pull_requests.py` also has no
`router`, which would prevent startup after fixing the first error.

No application endpoint is reachable through the original entry point. To
establish a compatibility baseline without changing the source, the health and
repository routers were mounted in a temporary TestClient application. Health,
URL parsing, metadata, commits, PRs, and changed files passed with mocked GitHub
responses. This is **not** a live GitHub integration claim.

### Original routes

| Method | Path | Baseline |
| --- | --- | --- |
| GET | `/health` | Passes isolated test |
| POST | `/repositories/parse-repo-url` | Passes isolated test |
| POST | `/repositories/repo/metadata` | Passes mocked isolated test |
| POST | `/repositories/repo/commits` | Passes mocked isolated test; `commits` envelope |
| POST | `/repositories/repo/pulls` | Passes mocked isolated test; `pulls` envelope |
| POST | `/repositories/repo/pulls/{pr_number}/files` | Passes mocked isolated test; `files` envelope |
| POST | `/scans` | Declared, cannot import |
| GET | `/scans/{scan_id}` | Declared, cannot import |

The prior monolith at `4541f4e` also exposed `/analyze` as a URL parser.
API docs routes are FastAPI defaults.

### Gaps

| State | Findings |
| --- | --- |
| Completed at source level | Thin app factory; health; GitHub request isolation; metadata mappings; normalized `contributors`; nullable `patch` retrieval |
| Partially completed | Basic checks in analyzer service; unprotected mutable memory store; request schemas; repository/PR routes |
| Needs refactor | Analyzer implementation embedded in coordinator; HTTPException in GitHub service; import-time environment loading; PR handlers inside repository router |
| Not started | Scoring; scan orchestration; completed scan API; tests; PostgreSQL/SQLAlchemy/Alembic; product frontend; external analyzers; AI; history; jobs; Docker/CI; SaaS |

GitHub calls have no timeouts, pagination, retry bounds, or reliable separation
of rate limits from permission failures. The basic analyzer scans deleted and
context lines, cannot locate findings, and treats keyword mentions as high-risk
secrets. Scans must not persist patches or matched credential values.

### Dependencies and tests

The existing pinned runtime requirements installed successfully in a clean
Python 3.12 environment. No tests or dev requirements existed. Add pytest,
TestClient's HTTP client, and Ruff for this milestone. SQLAlchemy, Alembic,
PostgreSQL drivers, shadcn/ui, Recharts, analyzer tools, OpenAI, Celery, and Redis
are absent and belong to subsequent milestones; do not install them merely to
fill placeholder folders.

## Immediate ordered work

| Task | Files affected | Why / acceptance criteria | Verification |
| --- | --- | --- | --- |
| M0: repair composition and contracts | `app/main.py`, `api/{repositories,pull_requests,compatibility,errors}.py`, `schemas/{repository,pull_request}.py` | App starts; canonical routes and existing envelopes work; compatibility aliases preserve original paths | TestClient route/response regression; live Uvicorn health/OpenAPI |
| M0: configuration and GitHub reliability | `core/{config,errors}.py`, `services/github_service.py`, `.env.example` | Credentials centralized; bounded timeouts/GET retries; all pages; safe error mapping; nullable patches | Mock success, invalid URL, 401/403/404/429, pagination, redirects, timeouts |
| M1: modular checks | `analyzers/basic_analyzer.py`, `services/analyzer_service.py`, `schemas/issue.py` | Canonical findings; added-line coordinates; all requested heuristics; no source in findings | Analyzer fixtures for added/deleted/context lines, tests, null patches, false positives |
| M1: deterministic scoring | `services/scoring_service.py` | Exact weights and boundaries; 1001+ lines adds 20, never 30; no PR-size double count | Parametrized boundary/weight tests |
| M1: scan workflow/storage/API | `services/scan_service.py`, `db/memory_store.py`, `schemas/scan.py`, `api/scans.py`, `app/main.py` | Pending/running/completed/failed; timings, metrics, issues and risk; fetchable failures; reusable service | API lifecycle, failure/privacy/concurrency tests; real public GitHub PR smoke scan |
| M1: handoff | `README.md`, `docs/BUILD_AUDIT.md`, `docs/VALIDATION.md` | Accurate setup, endpoints, scoring, privacy, limitations, roadmap; no unverified feature claims | Run documented commands and record exact outcomes |

## Subsequent milestones

After the deterministic flow is verified: PostgreSQL models and migrations →
Next.js product screens → isolated external analyzers → bounded structured AI
review → history/analytics → Celery/Redis → Docker/CI → GitHub App integration →
authentication and tenant ownership. Keep this first change focused on M0/M1.
