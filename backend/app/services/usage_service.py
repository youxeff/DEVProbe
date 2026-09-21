"""Reservations and plan limits share the scan-creation transaction."""

from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.core import context
from app.core.errors import ServiceError
from app.db.session import session_scope
from app.models import AuditLog, Membership, Organization, Repository, UsageCounter
from app.services.repository_service import upsert

LIMITS = {
    "free": {"scans": 50, "repositories": 5, "members": 3},
    "pro": {"scans": 1000, "repositories": 50, "members": 25},
}


def audit(session, organization_id, action, resource_id=None, *, user_id=None):
    if organization_id is not None:
        session.add(
            AuditLog(
                organization_id=organization_id,
                user_id=user_id if user_id is not None else context.user_id.get(),
                action=action,
                resource_id=str(resource_id) if resource_id is not None else None,
            )
        )


def lock_organization(session, organization_id):
    # A write acquires a lock on PostgreSQL and SQLite before any admission read.
    changed = session.execute(
        update(Organization)
        .where(Organization.id == organization_id)
        .values(updated_at=datetime.now(UTC))
    ).rowcount
    if not changed:
        raise ServiceError("Organization not found.", 404)
    return session.get(Organization, organization_id, populate_existing=True)


def check_repository_limit(session, organization_id, repo_url):
    if organization_id is None:
        return
    from app.services.github_service import parse_github_url

    owner, name = parse_github_url(repo_url)
    org = lock_organization(session, organization_id)
    existing = session.scalar(
        select(Repository.id).where(
            Repository.organization_id == organization_id,
            Repository.full_name == f"{owner}/{name}".lower(),
        )
    )
    count = session.scalar(
        select(func.count())
        .select_from(Repository)
        .where(Repository.organization_id == organization_id)
    )
    if not existing and count >= LIMITS[org.plan]["repositories"]:
        raise ServiceError("Repository limit reached for this plan.", 429)


def reserve_scan(session, organization_id, repo_url):
    if organization_id is None:
        return
    org = lock_organization(session, organization_id)
    check_repository_limit(session, organization_id, repo_url)
    period = datetime.now(UTC).strftime("%Y-%m")
    row = upsert(
        session,
        UsageCounter,
        {"organization_id": organization_id, "period": period, "scans": 0},
        ["organization_id", "period"],
        update=False,
    )
    changed = session.execute(
        update(UsageCounter)
        .where(UsageCounter.id == row.id, UsageCounter.scans < LIMITS[org.plan]["scans"])
        .values(scans=UsageCounter.scans + 1)
    ).rowcount
    if not changed:
        raise ServiceError("Monthly scan limit reached for this plan.", 429)


def usage(organization_id):
    period = datetime.now(UTC).strftime("%Y-%m")
    with session_scope() as session:
        org = session.get(Organization, organization_id)
        scans = (
            session.scalar(
                select(UsageCounter.scans).where(
                    UsageCounter.organization_id == organization_id, UsageCounter.period == period
                )
            )
            or 0
        )
        repositories = session.scalar(
            select(func.count())
            .select_from(Repository)
            .where(Repository.organization_id == organization_id)
        )
        members = session.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.organization_id == organization_id)
        )
        return {
            "plan": org.plan,
            "period": period,
            "scans": scans,
            "repositories": repositories,
            "members": members,
            "limits": LIMITS[org.plan],
        }
