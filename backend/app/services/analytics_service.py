from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core import context
from app.db.scan_store import snapshot
from app.db.session import session_scope
from app.models import Issue, Scan
from app.schemas.analytics import AnalyticsResponse, ScanPage, TrendPoint
from app.services.repository_service import get_repository

_CURRENT = object()


def conditions(repository_id=None, organization_id=_CURRENT):
    organization_id = (
        context.organization_id.get() if organization_id is _CURRENT else organization_id
    )
    if repository_id is not None:
        get_repository(repository_id, organization_id)
    return [Scan.organization_id == organization_id] + (
        [Scan.repository_id == repository_id] if repository_id is not None else []
    )


def history(*, repository_id=None, organization_id=_CURRENT, offset=0, limit=25) -> ScanPage:
    where = conditions(repository_id, organization_id)
    with session_scope() as session:
        total = session.scalar(select(func.count()).select_from(Scan).where(*where))
        rows = session.scalars(
            select(Scan)
            .options(selectinload(Scan.issues), selectinload(Scan.ai_review))
            .where(*where)
            .order_by(Scan.created_at.desc(), Scan.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return ScanPage(
            items=[snapshot(row) for row in rows], total=total, offset=offset, limit=limit
        )


def summary(repository_id=None, organization_id=_CURRENT) -> AnalyticsResponse:
    where = conditions(repository_id, organization_id)
    with session_scope() as session:
        counts = dict(
            session.execute(
                select(Scan.status, func.count()).where(*where).group_by(Scan.status)
            ).all()
        )
        completed = [*where, Scan.status == "completed"]
        stats = session.execute(
            select(
                func.count(func.distinct(Scan.pull_request_id)),
                func.sum(Scan.changed_files_count),
                func.sum(Scan.total_changed_lines),
                func.sum(Scan.total_issues),
                func.avg(Scan.risk_score),
                func.avg(Scan.scan_duration_seconds),
            ).where(*completed)
        ).one()
        tokens = session.execute(
            select(
                func.sum(Scan.ai_input_tokens),
                func.sum(Scan.ai_output_tokens),
                func.sum(Scan.ai_estimated_cost),
            ).where(*where)
        ).one()
        reviews = session.scalar(
            select(func.count()).select_from(Scan).where(*where, Scan.ai_status == "completed")
        )
        severity = dict(
            session.execute(
                select(Issue.severity, func.count())
                .join(Scan, Issue.scan_id == Scan.id)
                .where(*completed)
                .group_by(Issue.severity)
            ).all()
        )
        categories = dict(
            session.execute(
                select(Issue.category, func.count())
                .join(Scan, Issue.scan_id == Scan.id)
                .where(*completed)
                .group_by(Issue.category)
            ).all()
        )
        recent = session.execute(
            select(Scan.id, Scan.created_at, Scan.risk_score, Scan.total_issues)
            .where(*completed)
            .order_by(Scan.created_at.desc(), Scan.id.desc())
            .limit(30)
        ).all()
        total = sum(counts.values())
        return AnalyticsResponse(
            total_scans=total,
            completed_scans=counts.get("completed", 0),
            failed_scans=counts.get("failed", 0),
            prs_analyzed=stats[0] or 0,
            files_analyzed=stats[1] or 0,
            changed_lines_analyzed=stats[2] or 0,
            total_issues=stats[3] or 0,
            average_risk_score=stats[4],
            average_duration_seconds=stats[5],
            failure_rate=counts.get("failed", 0) / total if total else 0,
            ai_reviews=reviews,
            ai_input_tokens=tokens[0] or 0,
            ai_output_tokens=tokens[1] or 0,
            ai_estimated_cost=tokens[2],
            severity_counts=severity,
            category_counts=categories,
            trend=[
                TrendPoint(
                    scan_id=r.id,
                    created_at=r.created_at,
                    risk_score=r.risk_score,
                    total_issues=r.total_issues,
                )
                for r in reversed(recent)
            ],
        )
