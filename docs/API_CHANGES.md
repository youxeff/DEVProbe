# API compatibility and migrations

- Original canonical and legacy repository/PR routes remain registered. Commit, PR-list, and changed-file envelopes (`commits`, `pulls`, `files`) are preserved.
- `contributors` is normalized; the erroneous historical `contributors: ` key is not emitted. Changed files include nullable `patch`.
- Added repository IDs and SQL persistence. Repository identity is scoped to an organization and retains GitHub's stable repository ID when metadata is connected.
- `POST /scans` returns `{scan_id, status}`. Synchronous mode can return completed; asynchronous mode returns pending. Clients should always retrieve `/scans/{id}` and support pending/running/completed/failed. Failures after creation include `scan_id` so their persisted state can be inspected.
- Added individual PR detail (`POST /pull-requests/{number}`), list/history/analytics, account/organization, integration, billing, and signed webhook routes.
- `AUTH_ENABLED=false` preserves the local single-workspace API. With authentication enabled, all data routes, including compatibility aliases, require sessions and membership. Browser mutations require the configured `Origin` plus a session-bound CSRF token. This is an intentional opt-in security boundary; it is not silently applied to existing local-mode API clients.
- Legacy `organization_id=NULL` data stays unassigned. No first-login ownership inference or cross-tenant adoption occurs. Reconnect/rescan within the intended organization. A future explicit, audited migration command can transfer chosen historical data if required.
- Risk scoring stays version 1, uncapped. The >1,000-line penalty is +20 instead of +10. No normalized 0–100 score was introduced.
- Public API shapes are Pydantic/response contracts, not database row serialization. Internal tokens, password hashes, OAuth state/verifier values, provider secrets, and billing customer/subscription IDs are not exposed in general data responses.

Run `alembic upgrade head` before starting updated API/workers. The migrations create schema from a clean database and are tested through downgrade/re-upgrade. Back up existing deployment data before migrations; never use test migration commands against production.
