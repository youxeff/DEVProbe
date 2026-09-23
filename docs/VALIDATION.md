# Validation record

Date: 2026-09-19. Python 3.12.14. No GitHub PAT was supplied to the backend.

## Baseline

The original application failed startup with an ImportError for
`scan_service.create_scan_result`. Independently mounted health and repository
routers passed the isolated compatibility probes described in [BUILD_AUDIT.md](BUILD_AUDIT.md).

## Milestone 0

- 64 automated tests passed after refactoring.
- Ruff passed for all new/refactored M0 modules and tests.
- Uvicorn started and `/health` and `/openapi.json` returned HTTP 200.
- Real requests through the running API to `youxeff/DEVProbe` returned HTTP 200
  for repository metadata, commits, and the PR list (empty before this branch's PR).
- All original route envelopes and compatibility aliases were exercised with
  mocked GitHub responses, including changed files and nullable patches.

## Milestone 1

- 139 automated tests passed, including all M0 tests.
- Ruff, application import/bytecode compilation, and `git diff --check` passed.
- Test coverage includes URL validation, auth/permission/not-found/rate-limit
  mapping, continuation URL safety, pagination, bounded retry and size limits,
  diff line numbering, removed/context lines, test detection, canonical issue
  validation/deduplication, scoring weights and boundaries, scan success/failure,
  failure privacy, PR snapshot changes, incomplete retrieval, missing patches,
  concurrent IDs, atomic claim, and store snapshot isolation.
- The installed Starlette 1.2.0 emits one deprecation warning about TestClient's
  httpx adapter. It does not fail the tests. Existing runtime pins are retained;
  switching to httpx2 should be a separately tested dependency update because
  its current version requires a newer idna than this repository pins.

### Live HTTP scan

A real Uvicorn process called GitHub directly through `github_service`:

1. `GET /health` → 200.
2. `POST /scans` with `https://github.com/psf/requests`, PR `7616` →
   200, `{"scan_id": 1, "status": "completed"}`.
3. `GET /scans/1` → 200, completed result.

| Measured field | Value |
| --- | --- |
| PR | [psf/requests#7616](https://github.com/psf/requests/pull/7616) |
| Head SHA | `4cb8d62fe69e0fa95605b21b3f747cd858189c26` |
| Base SHA | `5460f467b02e49471c0fd6cfc9ca0adab6351f98` |
| Changed files | 1 |
| Additions / deletions | 1 / 1 |
| Changed lines | 2 |
| Files with a patch | 1 |
| Findings | 0 |
| Risk score / level | 0 / Low |
| Duration | 16.960698 seconds |
| Completed UTC | 2026-09-19T22:04:47.048052Z |

This was a dependency-configuration update, so zero findings is expected. A
separate synthetic API fixture containing an added print and TODO, with no test
updates, produces three findings and a score of 6. It is not represented as a
live repository result. An earlier public file request timed out; the service's
bounded retry subsequently recovered. Duration is one observation, not a
performance guarantee.

## Not validated or implemented in this change

PostgreSQL durability/migrations, product frontend, third-party analyzers,
OpenAI, asynchronous workers, Docker, CI workflows, GitHub App/webhooks/comments,
authentication, organization ownership, and billing. No production deployment.
No repository code or customer tests were executed.
