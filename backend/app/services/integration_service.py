"""Verified installation ownership and idempotent, application-controlled GitHub output."""

from contextlib import contextmanager

from sqlalchemy import func, select

from app.core import context
from app.core.errors import ServiceError
from app.db.session import session_scope
from app.models import GitHubCheck, GitHubInstallation
from app.services import github_service
from app.services.repository_service import upsert


def installation_for_owner(owner: str, organization_id: int | None):
    with session_scope() as session:
        return session.scalar(
            select(GitHubInstallation).where(
                GitHubInstallation.organization_id == organization_id,
                func.lower(GitHubInstallation.account_login) == owner.lower(),
                GitHubInstallation.active.is_(True),
            )
        )


@contextmanager
def repository_credentials(repo_url: str, organization_id: int | None):
    owner, _ = github_service.parse_github_url(repo_url)
    installation = installation_for_owner(owner, organization_id)
    token = context.installation_id.set(
        installation.github_installation_id if installation else None
    )
    try:
        yield installation
    finally:
        context.installation_id.reset(token)


def link_installation(
    organization_id: int | None, remote_id: int, user_token: str, *, user_id=None
):
    metadata = github_service.verify_installation_owner(user_token, remote_id)
    with session_scope() as session:
        if user_id is not None:
            from app.models import Membership
            from app.services.usage_service import audit, lock_organization

            lock_organization(session, organization_id)
            member = session.scalar(
                select(Membership).where(
                    Membership.user_id == user_id, Membership.organization_id == organization_id
                )
            )
            if not member or member.role not in {"owner", "admin"}:
                raise ServiceError("Organization administrator access is required.", 403)
            audit(session, organization_id, "github.connected", remote_id, user_id=user_id)
        row = upsert(
            session,
            GitHubInstallation,
            {**metadata, "organization_id": organization_id, "publish_checks": False},
            ["github_installation_id"],
            update=False,
        )
        if row.organization_id != organization_id:
            raise ServiceError("This installation is already linked to another organization.", 409)
        for key, value in metadata.items():
            setattr(row, key, value)
        return row.id


def publish_scan(scan, *, automatic=False):
    if scan.status != "completed" or not scan.head_sha or not scan.repository_id:
        raise ServiceError("Only a completed scan can be published.", 409)
    with repository_credentials(scan.repo_url, scan.organization_id) as installation:
        if not installation:
            if automatic:
                return None
            raise ServiceError("Connect a GitHub App installation first.", 409)
        if automatic and not installation.publish_checks:
            return None
        # Serialize output for this commit, including recovery after an ambiguous HTTP result.
        with session_scope() as session:
            row = upsert(
                session,
                GitHubCheck,
                {"repository_id": scan.repository_id, "head_sha": scan.head_sha},
                ["repository_id", "head_sha"],
                update=False,
            )
            row = session.scalar(
                select(GitHubCheck).where(GitHubCheck.id == row.id).with_for_update()
            )
            output = {
                "conclusion": "failure" if scan.risk_level in ("High", "Critical") else "neutral",
                "title": f"Risk {scan.risk_score} — {scan.risk_level}",
                "summary": (
                    f"DevProbe scan #{scan.id}: {scan.total_issues} findings across "
                    f"{scan.changed_files_count} changed files and "
                    f"{scan.total_changed_lines} lines.\n\n"
                    f"Security: {scan.security_count}; testing: {scan.testing_count}; "
                    f"complexity: {scan.complexity_count}.\n\n"
                    "Findings are review signals, not proof of security or test coverage. "
                    "Open DevProbe for the full review."
                ),
            }
            row.check_run_id = github_service.publish_check(
                scan.repo_url,
                scan.head_sha,
                f"devprobe:{scan.repository_id}:{scan.head_sha}",
                output,
                row.check_run_id,
            )
            row.scan_id = scan.id
            return {"check_run_id": row.check_run_id}


def settings_view():
    from app.core.config import get_settings
    from app.core.security import require_identity

    _, org = require_identity()
    settings = get_settings()
    with session_scope() as session:
        rows = session.scalars(
            select(GitHubInstallation).where(GitHubInstallation.organization_id == org)
        )
        return {
            "configured": bool(
                settings.github_app_id
                and settings.github_private_key
                and settings.github_client_id
                and settings.github_client_secret
            ),
            "install_url": (
                f"https://github.com/apps/{settings.github_app_slug}/installations/new"
                if settings.github_app_slug
                else None
            ),
            "installations": [
                {
                    "id": row.id,
                    "github_installation_id": row.github_installation_id,
                    "account_login": row.account_login,
                    "active": row.active,
                    "publish_checks": row.publish_checks,
                }
                for row in rows
            ],
        }


def start_connection(remote_id):
    import base64
    import hashlib
    from datetime import UTC, datetime, timedelta
    from urllib.parse import urlencode

    from sqlalchemy import delete

    from app.core.config import get_settings
    from app.core.security import digest, new_token, require_identity, require_role
    from app.models import GitHubOAuthState

    user, org = require_identity()
    require_role("admin")
    settings = get_settings()
    if not settings_view()["configured"]:
        raise ServiceError("GitHub App authorization is not configured.", 503)
    state, verifier = new_token(), new_token()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    with session_scope() as session:
        session.execute(
            delete(GitHubOAuthState).where(GitHubOAuthState.expires_at < datetime.now(UTC))
        )
        session.add(
            GitHubOAuthState(
                state_hash=digest(state),
                user_id=user,
                organization_id=org,
                github_installation_id=remote_id,
                code_verifier=verifier,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
    return {
        "url": "https://github.com/login/oauth/authorize?"
        + urlencode(
            {
                "client_id": settings.github_client_id,
                "state": state,
                "redirect_uri": settings.public_url + "/api/backend/github/callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    }


def finish_connection(code, state):
    from datetime import UTC, datetime

    from sqlalchemy import delete

    from app.core.security import digest, require_identity
    from app.models import GitHubOAuthState, Membership

    user, _ = require_identity()
    with session_scope() as session:
        saved = session.execute(
            delete(GitHubOAuthState)
            .where(
                GitHubOAuthState.state_hash == digest(state),
                GitHubOAuthState.user_id == user,
                GitHubOAuthState.expires_at > datetime.now(UTC),
            )
            .returning(GitHubOAuthState)
        ).scalar_one_or_none()
        if saved is None:
            raise ServiceError("GitHub authorization state is invalid or expired.", 400)
        member = session.scalar(
            select(Membership).where(
                Membership.user_id == user, Membership.organization_id == saved.organization_id
            )
        )
        if not member or member.role not in {"owner", "admin"}:
            raise ServiceError("Organization administrator access is required.", 403)
    token = github_service.exchange_oauth_code(code, saved.code_verifier)
    link_installation(saved.organization_id, saved.github_installation_id, token, user_id=user)


def update_installation(installation_id, *, publish_checks=None, disconnect=False):
    from app.core.security import require_identity, require_role
    from app.services.usage_service import audit

    _, org = require_identity()
    require_role("admin")
    with session_scope() as session:
        row = session.scalar(
            select(GitHubInstallation).where(
                GitHubInstallation.id == installation_id, GitHubInstallation.organization_id == org
            )
        )
        if not row:
            raise ServiceError("Installation not found.", 404)
        if disconnect:
            row.active, row.publish_checks = False, False
            with github_service._token_lock:
                github_service._token_cache.pop(row.github_installation_id, None)
        elif publish_checks is not None:
            if not row.active:
                raise ServiceError("Reconnect this installation first.", 409)
            row.publish_checks = publish_checks
        audit(
            session, org, "github.disconnected" if disconnect else "github.settings_updated", row.id
        )
        return {"status": "updated"}


def publish_for_user(scan_id):
    from app.core.security import require_identity, require_role
    from app.services import scan_service
    from app.services.usage_service import audit

    _, org = require_identity()
    require_role("member")
    result = publish_scan(scan_service.get_scan(scan_id))
    with session_scope() as session:
        audit(session, org, "github.check_published", scan_id)
    return result
