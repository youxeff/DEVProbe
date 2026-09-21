"""SQL pending scans are durable work records; Redis carries only their IDs."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update

from app.core.config import get_settings
from app.db.session import session_scope
from app.models import Scan
from app.services import scan_service

logger = logging.getLogger(__name__)


def submit(repo_url: str, pr_number: int):
    if get_settings().scan_mode == "sync":
        return scan_service.create_scan(repo_url, pr_number)
    scan = scan_service.create_pending_scan(repo_url, pr_number)
    dispatch(scan.id)
    return scan


def dispatch(scan_id: int) -> bool:
    from app.workers.scan_worker import run_scan

    now = datetime.now(UTC)
    with session_scope() as session:
        claimed = session.execute(
            update(Scan)
            .where(
                Scan.id == scan_id,
                Scan.status == "pending",
                or_(Scan.queued_at.is_(None), Scan.queued_at < now - timedelta(seconds=60)),
            )
            .values(queued_at=now, dispatch_attempts=Scan.dispatch_attempts + 1)
        ).rowcount
    if not claimed:
        return False
    try:
        run_scan.apply_async(args=[scan_id], task_id=f"scan-{scan_id}", retry=False)
        return True
    except Exception as error:
        # Keep pending for the recovery scheduler; the API never loses an accepted job.
        logger.warning(
            "scan_dispatch_failed scan_id=%s error_type=%s", scan_id, type(error).__name__
        )
        return False


def recover() -> dict:
    now = datetime.now(UTC)
    with session_scope() as session:
        expired = session.execute(
            update(Scan)
            .where(Scan.status == "running", Scan.started_at < now - timedelta(seconds=900))
            .values(
                status="failed",
                completed_at=now,
                failure_reason="Worker stopped or exceeded its execution window. Start a new scan.",
            )
        ).rowcount
        ids = list(
            session.scalars(
                select(Scan.id)
                .where(
                    Scan.status == "pending",
                    or_(Scan.queued_at.is_(None), Scan.queued_at < now - timedelta(seconds=60)),
                )
                .order_by(Scan.id)
                .limit(100)
            )
        )
    dispatched = sum(dispatch(scan_id) for scan_id in ids)
    return {"dispatched": dispatched, "expired": expired}
