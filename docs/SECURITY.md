# Security boundaries and deployment notes

## Enforced in this build

Passwords use Argon2id (19 MiB, two iterations, one lane). Session and CSRF tokens are random; only hashes are stored. Session cookies are HttpOnly, SameSite=Lax, and Secure on HTTPS. A session expires after 24 hours by default; sign-out revokes it, and password changes revoke every user session. Password and registration requests have SQL-backed throttling. JSON validation responses omit submitted values.

Identity middleware establishes request context from a valid session and verified membership, then resets it. Object reads, list queries, analytics, integration settings, and history respect organization ownership. A worker derives its organization from its stored scan, never a caller-supplied tenant ID. Legacy unowned rows are not visible to authenticated organizations. Missing membership cannot fall back to the unowned workspace. Tenant isolation is application-enforced, not PostgreSQL RLS.

CSRF checks compare the configured browser Origin and a token tied to the session. GitHub/Stripe webhook routes are public only because they validate provider signatures over bounded raw bodies. GitHub OAuth uses random, expiring, one-time state plus PKCE and re-checks organization administrator permission before associating an installation. Installation ownership is verified with GitHub, not inferred from possession of an installation ID.

Repository content is untrusted. File requests are SHA-pinned and size-limited; filenames cannot escape a temporary directory. Analyzer inputs use synthetic safe filenames. Only installed, application-selected tools and owned rule/config files run. Tool subprocesses receive no provider credentials or production environment variables, have CPU/output/file limits and deadlines, and are killed as a process group on timeout. No repository pytest, npm scripts, installs, hooks, build steps, or configuration plugins run.

Full source and patches are transient. Findings contain generic, application-owned messages, not matched source or secret literals. SQL stores metadata, coordinates, findings, metrics, structured AI reviews, and bounded tool-execution summaries. AI receives bounded findings/metrics only and no tools. A model response cannot trigger GitHub output. Check output contains application-owned metrics, is opt-in/explicit, and uses stable commit identities.

Request logs contain a generated request ID, route template, status, organization ID, and duration. They omit headers, bodies, query strings, and exception payloads. Use the documented `--no-access-log` Uvicorn command: generic access logs can include OAuth codes in query strings. Do not enable upstream HTTP debug logging with customer data.

## Deployment work still outstanding

- Run native PostgreSQL/Compose and remote CI gates. Use managed secrets and TLS, with `APP_ENV=production` and `AUTH_ENABLED=true`. Startup validates HTTPS and PostgreSQL. Keep database/Redis networks private.
- Put analysis in dedicated ephemeral OS/container isolation with restricted egress/filesystem access before hostile multi-customer hosting. Existing subprocess/resource controls are useful, but do not claim a complete sandbox or execute customer tests yet.
- Apply edge request-size/rate limits and configure trusted reverse proxies. The login throttle uses the server-observed client address; a shared reverse proxy can otherwise aggregate clients. Do not trust arbitrary forwarded IP headers.
- Review exact image SBOM/licensing, pin release image digests, and configure backup/restore, data retention, monitoring, and operational access controls. The current source is a SaaS foundation, not a security certification.
- Registration does not verify email ownership or send mail. Invitation possession plus matching-account email grants team membership. Deliver invitation links securely. Email verification, password recovery delivery, MFA/SSO, and account deletion/retention workflows remain future account-lifecycle work.
- Stripe and GitHub/OpenAI activation require live/test provider account verification. Use Stripe test mode first; no keys or real payment method data are included in this repository.

Design references: [OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [GitHub OAuth and PKCE](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app).
