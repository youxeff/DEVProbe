# DevProbe end-to-end walkthrough

This walkthrough explains the implemented product and how to operate it. Start with the browser flow, then read the sections for automation and provider activation. The [validation ledger](MILESTONE_VALIDATION.md) separates actual checks from unverified external deployment steps.

## 1. Start the application

The local quickstart in [README.md](../README.md#local-setup) runs SQLite, synchronous scans, and the basic analyzer with no provider key required for public GitHub repositories. Use `http://localhost:3000` so the browser origin matches `PUBLIC_URL`.

To include accounts, set `AUTH_ENABLED=true` in `backend/.env` and restart the backend. To include PostgreSQL, Redis, and separate workers, use the Compose instructions in the README. Compose was syntax-validated here; run its actual build/boot gate on a Docker-capable machine before calling it verified.

The first screen asks you to sign in when authentication is enabled. Choose **Create an account**, enter your name, email, password of at least 12 characters, and organization name. Your account becomes that organization's owner. No email is sent or email ownership certified by this registration flow.

## 2. Connect a repository

Enter a GitHub repository URL and click **Analyze repository**. Public repositories work anonymously subject to GitHub's rate limit. Authenticated organizations need a verified GitHub App installation for private repositories; a development PAT does not grant a tenant access.

The repository screen shows its description, language, default branch, stars, forks, open issue count, contributors, and open pull requests. GitHub errors are displayed as actionable errors rather than an empty success screen.

## 3. Inspect a pull request

Choose a PR from the list. The detail screen shows title, author, state, and file additions/deletions. Files without a text patch are allowed, but their added-line checks cannot run. GitHub pagination is followed and a scan refuses incomplete or changing file lists.

## 4. Run the scan

Click **Analyze PR**. The server first creates a durable pending scan and reserves one scan against the organization's monthly quota.

- In synchronous mode, the API runs the workflow and returns the completed or failed scan ID.
- In asynchronous mode, the API queues the ID and returns immediately. The page polls while the scan is pending/running. Redis does not carry tokens, source code, or an organization ID supplied by the caller.

The worker claims the scan once, loads its organization, fetches the PR, checks that the head/base are stable, gets changed files, runs the configured analyzers, calculates metrics and risk, optionally requests AI explanation, and saves the outcome. Queue redelivery does not run completed analysis twice. Pending jobs recover after broker outages; a worker that exceeds its execution window leaves a failed, inspectable result.

## 5. Read the result

The result screen gives you the uncapped score and risk level, issue count, file/line count, duration, and severity/category charts. Filter the table by severity, category, file, or tool. Each finding includes its path, line where available, tool, message, and recommendation.

Open **Analysis scope & limitations**. This explains absent patches, skipped files, size bounds, and analyzer errors. A small score does not prove that code is safe. A missing-test finding means no test additions were detected in the PR, not that the repository has no tests.

The test fixture intentionally produces this trace:

| Fixture signal | Points |
| --- | ---: |
| Possible quoted sensitive literal in `src/auth.py` | 10 |
| Debug `print()` in added code | 2 |
| Application code changes without test additions | 4 |
| TODO maintainability finding | 0 |
| **4 findings; 2 files; 6 changed lines** | **16 — Low** |

Those values belong only to the controlled fixture, not to a real customer repository. Automated browser tests check the complete flow and the displayed AI fixture. To operate that same reproducible demo manually, start the test server from `backend` after installing development dependencies:

```bash
DATABASE_URL=sqlite:///./demo.db alembic upgrade head
DATABASE_URL=sqlite:///./demo.db AUTH_ENABLED=true PUBLIC_URL=http://localhost:3000 SCAN_MODE=sync uvicorn tests.e2e_server:app --host 127.0.0.1 --port 8000 --no-access-log
```

Run the normal frontend on port 3000, then enter `https://github.com/devprobe-fixtures/review-lab`. **This server replaces GitHub and AI provider responses with fixtures.** It still uses the real API, database, basic analyzer, risk service, authorization, and UI. `app.main:app` is the production entry point and never imports this fixture.

## 6. Compare history

Open **Scan history**. It reports actual completed/failed totals, averages, risk trend, issue trend, and paginated scans. Run a second scan to get another historical point. Repository pages also list their own previous scans. Refresh or restart the API; SQL-backed results remain retrievable.

History queries are scoped to the selected organization. Changing the top-bar organization reloads the workspace and clears the previous page's in-memory UI state. Directly opening another organization's repository or scan ID returns not found.

## 7. Manage a team

Open **Settings** to see the current plan and quotas, members, GitHub connections, and audit activity.

| Role | Access |
| --- | --- |
| Viewer | Read repositories, PRs, results, and history |
| Member | Viewer access plus repository connection, scans, and explicit Check publication |
| Admin | Member access plus invitations, non-owner member management, integration settings, and audit records |
| Owner | Admin access plus ownership management and billing |

Create an invitation by email and role. Share the generated link with that intended recipient yourself. Links expire after 48 hours and can be accepted once, by a signed-in account with the matching email. The secret is in the URL fragment, so it is not sent as a request URL/query string. No mail delivery service is implemented. The last owner cannot be removed or demoted.

Quota admission is atomic. Free includes 50 accepted scans/month, 5 repositories, and 3 members; Pro includes 1,000/50/25. Failed accepted scans still count. AI input/output tokens and known cost estimates are recorded separately.

## 8. Turn on real AI review

Set these server-side variables and restart both API and worker processes:

```dotenv
AI_ENABLED=true
OPENAI_API_KEY=YOUR_SERVER_SIDE_KEY
OPENAI_MODEL=gpt-4.1-mini
```

Use a currently available model supporting strict structured output. If you want estimates, set verified current input/output prices per million tokens. Leaving prices blank keeps cost unknown.

The model receives findings and metrics, bounded to 20,000 characters, 50 findings, and 30 file paths. It receives no patches, source files, GitHub tokens, database credentials, or arbitrary repository instructions. Its result is validated into summary, risks, suggested tests, and recommended fixes. No AI call publishes to GitHub. Static analysis survives provider failures.

No live OpenAI request was verified here because no key was configured. [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## 9. Connect a GitHub App and enable automatic review

Create a GitHub App in the intended owner account. Configure repository permissions for **Metadata read**, **Contents read**, **Pull requests read**, and **Checks read/write**. For linking GitHub organization accounts, grant the organization membership-read permission needed to verify an active organization administrator. Subscribe to pull-request events and installation changes.

Use these URLs for a deployment whose public URL is `https://devprobe.example`:

| App setting | URL |
| --- | --- |
| User authorization callback | `https://devprobe.example/api/backend/github/callback` |
| Webhook | `https://devprobe.example/api/backend/webhooks/github` |

Set `PUBLIC_URL`, the App ID/slug/private key, client ID/secret, and webhook secret in the server environment. Configure `SCAN_MODE=async` and start Redis, a worker, and the scheduler. A localhost-only site cannot receive GitHub webhook deliveries; use a real HTTPS deployment for this activation step.

In **Settings → GitHub connection**, install the App on selected repositories, then enter the installation ID from its GitHub settings and click **Verify and connect**. OAuth state is one-time and user/organization bound, with PKCE. DevProbe verifies that the GitHub user owns the account or administers the organization before linking it. The user token is discarded; installation access tokens are short-lived and cached only in memory.

Opened, synchronize, reopened, and ready-for-review events create queued scans after HMAC verification. Drafts and unknown/revoked installations are ignored. Delivery and commit keys deduplicate retries. A webhook scan whose commit is no longer the PR head fails explicitly rather than analyzing the wrong revision.

Enable **Publish Checks after scans** to opt in to automatic Check output. Or click **Publish GitHub Check** on a completed result. Repeated publication updates the same repository/commit Check; remote `external_id` lookup recovers ambiguous responses. High/Critical risk yields a failure conclusion; Low/Medium yields neutral, not a security approval. Comments are not posted because Checks are the implemented GitHub output strategy.

These App/OAuth/webhook/Check paths were tested with mocked GitHub transport; actual App installation and external delivery require your configured account. [App tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app), [webhook signatures](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).

## 10. Activate billing only when ready

Create a recurring Pro price in Stripe test mode. Configure its server-side price ID, secret key, and webhook signing secret. Configure the Stripe webhook endpoint at `/api/backend/webhooks/stripe` for checkout completion and subscription created/updated/deleted events. Configure Stripe's customer portal for subscription/payment-method management.

An owner can open **Upgrade to Pro** or **Manage billing**. Checkout uses the server's configured price, not a browser-supplied plan/amount. A checkout return URL never grants Pro. A verified webhook fetches the customer's current subscriptions and updates the plan, so duplicate or out-of-order events cannot replay an old plan state. Active/trialing subscriptions to the configured price grant Pro; other states retain/revert to Free.

The implementation does not collect card numbers or initiate charges on its own. A user must complete hosted Checkout. No real payment was initiated or tested here. [Stripe Checkout](https://docs.stripe.com/api/checkout/sessions/create), [signature validation](https://docs.stripe.com/webhooks/signature).

## What still requires an external environment

The repository contains the application and deployment definitions. Completing production activation requires a Docker/native PostgreSQL run, successful remote CI, real provider credentials and webhook delivery tests, HTTPS hosting, worker isolation/egress controls, backup/retention operations, and final dependency/image license review. The current GitHub connection refused repository writes, so no remote branch/PR or deployment is claimed.
