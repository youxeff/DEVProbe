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


def link_installation(organization_id: int | None, remote_id: int, user_token: str):
    metadata = github_service.verify_installation_owner(user_token, remote_id)
    with session_scope() as session:
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
