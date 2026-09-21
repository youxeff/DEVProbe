"""SQL-backed scan snapshots; each operation owns a short transaction."""

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from app.core.errors import ServiceError
from app.db.session import session_scope
from app.models import Issue, PullRequest, Scan
from app.schemas.issue import IssueResponse
from app.schemas.scan import ScanResponse
from app.services.repository_service import ensure_pull_request, ensure_repository


def snapshot(row: Scan) -> ScanResponse:
    values = {
        key: getattr(row, key)
        for key in ScanResponse.model_fields
        if key != "issues" and hasattr(row, key)
    }
    for key in ("created_at", "started_at", "completed_at"):
        if values.get(key) and values[key].tzinfo is None:
            values[key] = values[key].replace(tzinfo=UTC)
    values["issues"] = [
        IssueResponse.model_validate(
            {key: getattr(issue, key) for key in IssueResponse.model_fields}
        )
        for issue in row.issues
    ]
    return ScanResponse.model_validate(values)


class SQLScanStore:
    def create(self, scan: ScanResponse) -> ScanResponse:
        with session_scope() as session:
            repo = ensure_repository(session, scan.repo_url, scan.organization_id)
            pull = ensure_pull_request(session, repo.id, scan.pr_number)
            values = scan.model_dump(exclude={"id", "issues", "repository_id", "pull_request_id"})
            row = Scan(**values, repository_id=repo.id, pull_request_id=pull.id)
            session.add(row)
            session.flush()
            return snapshot(row)

    def get(self, scan_id: int) -> ScanResponse | None:
        with session_scope() as session:
            row = session.scalar(
                select(Scan).options(selectinload(Scan.issues)).where(Scan.id == scan_id)
            )
            return snapshot(row) if row else None

    def claim(self, scan_id: int) -> tuple[ScanResponse, bool]:
        with session_scope() as session:
            result = session.execute(
                update(Scan)
                .where(Scan.id == scan_id, Scan.status == "pending")
                .values(status="running", started_at=datetime.now(UTC))
            )
            row = session.scalar(
                select(Scan).options(selectinload(Scan.issues)).where(Scan.id == scan_id)
            )
            if row is None:
                raise ServiceError("Scan not found.", 404)
            return snapshot(row), result.rowcount == 1

    def save(self, scan: ScanResponse) -> None:
        with session_scope() as session:
            row = session.get(Scan, scan.id)
            if row is None:
                raise ServiceError("Scan not found.", 404)
            for key, value in scan.model_dump(exclude={"id", "issues"}).items():
                setattr(row, key, value)
            session.execute(delete(Issue).where(Issue.scan_id == scan.id))
            session.add_all([Issue(scan_id=scan.id, **issue.model_dump()) for issue in scan.issues])

    def update_pull_request(self, scan_id: int, metadata: dict) -> None:
        with session_scope() as session:
            scan = session.get(Scan, scan_id)
            pull = session.get(PullRequest, scan.pull_request_id)
            for key in ("title", "state", "author", "html_url", "base_branch", "head_branch"):
                if key in metadata:
                    setattr(pull, key, metadata[key])
            for source, target in (
                ("created_at", "github_created_at"),
                ("updated_at", "github_updated_at"),
            ):
                if metadata.get(source):
                    setattr(pull, target, datetime.fromisoformat(metadata[source]))

    def history(self, repository_id: int, *, offset=0, limit=100) -> list[ScanResponse]:
        with session_scope() as session:
            rows = session.scalars(
                select(Scan)
                .options(selectinload(Scan.issues))
                .where(Scan.repository_id == repository_id)
                .order_by(Scan.created_at.desc(), Scan.id.desc())
                .offset(offset)
                .limit(limit)
            )
            return [snapshot(row) for row in rows]
