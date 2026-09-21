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
