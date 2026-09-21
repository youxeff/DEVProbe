from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.db import session as db_session
from app.db.database import build_engine
from app.db.scan_store import SQLScanStore
from app.db.session import session_scope
from app.models import Issue, PullRequest, Repository, Scan
from app.services import repository_service, scan_service

PAYLOAD = {"repo_url": "https://github.com/owner/repo", "pr_number": 12}


def test_migration_from_clean_database_and_downgrade(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = build_engine(url)
    assert {"repositories", "pull_requests", "scans", "issues", "ai_reviews"} <= set(
        inspect(engine).get_table_names()
    )
    command.check(config)
    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    command.upgrade(config, "head")
    engine.dispose()


def test_persisted_scan_survives_new_store(
    client, monkeypatch, response, github_mock, pull_data, file_data
):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    github_mock(response(pull_data), response([file_data]), response(pull_data))
    assert client.post("/scans", json=PAYLOAD).json()["status"] == "completed"
    db_session.get_engine().dispose()
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    saved = client.get("/scans/1").json()
    assert saved["status"] == "completed" and saved["risk_score"] == 6
    assert len(saved["issues"]) == 3
    history = client.get(f"/repositories/{saved['repository_id']}/scans")
    assert history.status_code == 200 and history.json()[0]["id"] == 1
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(Repository)) == 1
        assert session.scalar(select(func.count()).select_from(PullRequest)) == 1
        assert session.scalar(select(PullRequest.title)) == pull_data["title"]


def test_pr_uniqueness_and_cascade(monkeypatch):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    scan_service.create_pending_scan(**PAYLOAD)
    with pytest.raises(IntegrityError), session_scope() as session:
        session.add(PullRequest(repository_id=1, github_pr_number=12))
        session.flush()
    with session_scope() as session:
        session.add(
            Issue(
                scan_id=1,
                file_path="test.py",
                tool="test",
                category="testing",
                severity="info",
                message="test",
                recommendation="test",
            )
        )
    with session_scope() as session:
        session.delete(session.get(Repository, 1))
    with session_scope() as session:
        for model in (PullRequest, Scan, Issue):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_persistent_claim_is_atomic(monkeypatch):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    scan = scan_service.create_pending_scan(**PAYLOAD)
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda _: SQLScanStore().claim(scan.id)[1], range(12)))
    assert sum(claims) == 1


def test_repeated_scans_reuse_repo_and_pr(monkeypatch):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    one = scan_service.create_pending_scan(**PAYLOAD)
    two = scan_service.create_pending_scan(**PAYLOAD)
    assert one.id != two.id
    assert one.repository_id == two.repository_id
    assert one.pull_request_id == two.pull_request_id


def test_connect_preserves_github_identity_after_rename(response, github_mock, repository_data):
    github_mock(
        response(repository_data),
        response([]),
        response({**repository_data, "name": "renamed", "full_name": "owner/renamed"}),
        response([]),
    )
    first = repository_service.connect_repository(PAYLOAD["repo_url"])
    second = repository_service.connect_repository("https://github.com/owner/renamed")
    assert first["id"] == second["id"]
    assert repository_service.get_repository(first["id"])["name"] == "renamed"


def test_repo_scope_prevents_cross_scope_read(response, github_mock, repository_data):
    from app.models import Organization

    with session_scope() as session:
        session.add(Organization(id=17, name="Scope test"))
    github_mock(response(repository_data), response([]))
    repo = repository_service.connect_repository(PAYLOAD["repo_url"], organization_id=17)
    from app.core.errors import ServiceError

    with pytest.raises(ServiceError):
        repository_service.get_repository(repo["id"], organization_id=18)
    assert repository_service.get_repository(repo["id"], organization_id=17)["github_repo_id"] == 42
