"""Use only with a dedicated test database via POSTGRES_TEST_URL."""

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select

from app.db import session as db_session
from app.db.database import build_engine
from app.db.scan_store import SQLScanStore
from app.db.session import session_scope
from app.models import Issue, Repository, Scan
from app.schemas.issue import IssueResponse
from app.services import scan_service


def main():
    url = os.environ["POSTGRES_TEST_URL"]
    if not url.startswith(("postgresql", "postgres:")):
        raise SystemExit("A PostgreSQL test URL is required.")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    command.check(config)
    engine = build_engine(url)
    db_session.get_engine = lambda: engine
    scan_service.store = SQLScanStore()
    scan = scan_service.create_pending_scan(
        f"https://github.com/devprobe-fixtures/test-{uuid4().hex}", 1
    )
    try:
        scan, claimed = SQLScanStore().claim(scan.id)
        assert claimed and not SQLScanStore().claim(scan.id)[1]
        scan.status = "completed"
        scan.risk_score = 10
        scan.risk_level = "Low"
        scan.issues = [
            IssueResponse(
                file_path="a.py",
                tool="test",
                category="security",
                severity="high",
                message="Fixture finding",
                recommendation="Review",
            )
        ]
        scan.total_issues = 1
        SQLScanStore().save(scan)
        engine.dispose()
        saved = SQLScanStore().get(scan.id)
        assert saved.issues[0].severity == "high" and saved.risk_score == 10
        with session_scope() as session:
            session.execute(delete(Repository).where(Repository.id == scan.repository_id))
        with session_scope() as session:
            assert session.get(Scan, scan.id) is None
            assert session.scalar(select(Issue).where(Issue.scan_id == scan.id)) is None
        print(
            "PASS: PostgreSQL migrations, JSONB, atomic claim, reconnect persistence, and cascades."
        )
    finally:
        with session_scope() as session:
            session.execute(delete(Repository).where(Repository.id == scan.repository_id))
        engine.dispose()


if __name__ == "__main__":
    main()
