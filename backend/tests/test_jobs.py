from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.db.scan_store import SQLScanStore
from app.db.session import session_scope
from app.models import Scan
from app.services import job_service, scan_service
from app.workers.scan_worker import run_scan

PAYLOAD = {"repo_url": "https://github.com/owner/repo", "pr_number": 12}


def test_async_api_returns_pending_and_worker_uses_same_workflow(
    client, monkeypatch, response, github_mock, pull_data, file_data
):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    monkeypatch.setattr(job_service, "get_settings", lambda: Settings(scan_mode="async"))
    calls = []
    monkeypatch.setattr(run_scan, "apply_async", lambda **kwargs: calls.append(kwargs))
    result = client.post("/scans", json=PAYLOAD)
    assert result.json() == {"scan_id": 1, "status": "pending"}
    assert calls[0]["args"] == [1]
    github_mock(response(pull_data), response([file_data]), response(pull_data))
    assert run_scan(1) == {"scan_id": 1, "status": "completed"}
    started = scan_service.get_scan(1).started_at
    assert run_scan(1)["status"] == "completed"
    assert scan_service.get_scan(1).started_at == started


def test_dispatch_failure_is_durable_and_recovery_marks_stale_running(monkeypatch):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    scan = scan_service.create_pending_scan(**PAYLOAD)

    def fail(**kwargs):
        raise ConnectionError("broker-secret")

    monkeypatch.setattr(run_scan, "apply_async", fail)
    assert not job_service.dispatch(scan.id)
    assert scan_service.get_scan(scan.id).status == "pending"
    with session_scope() as session:
        row = session.get(Scan, scan.id)
        row.status = "running"
        row.started_at = datetime.now(UTC) - timedelta(seconds=1000)
    assert job_service.recover()["expired"] == 1
    saved = scan_service.get_scan(scan.id)
    assert saved.status == "failed" and "broker-secret" not in saved.failure_reason
