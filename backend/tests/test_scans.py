from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest

from app.core.errors import ServiceError
from app.db.memory_store import MemoryScanStore
from app.services import analyzer_service, scan_service

PAYLOAD = {"repo_url": "https://github.com/owner/repo", "pr_number": 12}


def test_complete_scan(client, response, github_mock, pull_data, file_data):
    mock = github_mock(response(pull_data), response([file_data]), response(pull_data))
    created = client.post("/scans", json=PAYLOAD)
    assert created.status_code == 200
    assert created.json() == {"scan_id": 1, "status": "completed"}
    result = client.get("/scans/1").json()
    assert result["changed_files_count"] == 1
    assert result["additions"] == 2 and result["deletions"] == 1
    assert result["total_changed_lines"] == 3
    assert result["total_issues"] == 3
    assert result["risk_score"] == 6 and result["risk_level"] == "Low"
    assert result["style_count"] == result["testing_count"] == result["maintainability_count"] == 1
    assert result["security_count"] == 0
    assert result["head_sha"] == "a" * 40
    assert result["files_with_patch"] == 1
    assert result["scan_duration_seconds"] >= 0
    times = [
        datetime.fromisoformat(result[key]) for key in ("created_at", "started_at", "completed_at")
    ]
    assert times == sorted(times) and all(t.tzinfo for t in times)
    assert "patch" not in result and "files" not in result
    assert mock.call_count == 3


def test_missing_patch_explains_analysis_limit(client, response, github_mock, pull_data, file_data):
    github_mock(response(pull_data), response([{**file_data, "patch": None}]), response(pull_data))
    assert client.post("/scans", json=PAYLOAD).status_code == 200
    result = client.get("/scans/1").json()
    assert result["files_without_patch"] == 1
    assert any("no textual patch" in warning for warning in result["analysis_warnings"])
    assert result["risk_score"] == 4


@pytest.mark.parametrize(
    "status,headers,expected",
    [
        (404, {}, 404),
        (401, {}, 401),
        (403, {}, 403),
        (403, {"Retry-After": "60"}, 429),
    ],
)
def test_failed_scans_are_retrievable(client, response, github_mock, status, headers, expected):
    github_mock(response({"message": "sensitive upstream value"}, status, headers))
    result = client.post("/scans", json=PAYLOAD)
    assert result.status_code == expected
    assert result.json()["scan_id"] == 1
    failed = client.get("/scans/1").json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == result.json()["detail"]
    assert failed["completed_at"] and failed["started_at"]
    assert failed["risk_score"] is None
    assert "sensitive upstream value" not in str(failed)


def test_internal_failure_does_not_leak_source(
    client, response, github_mock, pull_data, file_data, monkeypatch, caplog
):
    github_mock(response(pull_data), response([file_data]), response(pull_data))

    def failing_analyzer(files):
        raise RuntimeError("source-or-token-must-not-leak")

    monkeypatch.setattr(analyzer_service, "analyze_changed_files", failing_analyzer)
    result = client.post("/scans", json=PAYLOAD)
    assert result.status_code == 500
    assert result.json()["scan_id"] == 1
    assert "source-or-token-must-not-leak" not in result.text + caplog.text
    stored = client.get("/scans/1").json()
    assert stored["status"] == "failed"
    assert stored["issues"] == [] and stored["risk_score"] is None


def test_secret_value_not_in_result_or_logs(
    client, response, github_mock, pull_data, file_data, caplog
):
    file_data["patch"] = '@@ -0,0 +1 @@\n+password = "sensitive-test-only-marker"'
    github_mock(response(pull_data), response([file_data]), response(pull_data))
    assert client.post("/scans", json=PAYLOAD).status_code == 200
    result = client.get("/scans/1")
    assert "sensitive-test-only-marker" not in result.text + caplog.text
    assert result.json()["security_count"] == 1


def test_invalid_requests_and_unknown_scan(client):
    for pr_number in (0, -1, True, "12"):
        assert client.post("/scans", json={**PAYLOAD, "pr_number": pr_number}).status_code == 422
    assert client.post("/scans", json={**PAYLOAD, "repo_url": "bad"}).status_code == 400
    assert client.get("/scans/999").status_code == 404


def test_incomplete_file_list_fails(client, response, github_mock, pull_data):
    github_mock(response(pull_data), response([]))
    assert client.post("/scans", json=PAYLOAD).status_code == 409
    assert client.get("/scans/1").json()["status"] == "failed"


def test_pr_changed_during_fetch(client, response, github_mock, pull_data, file_data):
    latest = {**pull_data, "head": {"sha": "c" * 40}}
    github_mock(response(pull_data), response([file_data]), response(latest))
    assert client.post("/scans", json=PAYLOAD).status_code == 409


def test_github_file_limit(client, response, github_mock, pull_data):
    github_mock(response({**pull_data, "changed_files": 3001}))
    assert client.post("/scans", json=PAYLOAD).status_code == 422


def test_patch_size_limit(client, response, github_mock, pull_data, file_data, monkeypatch):
    monkeypatch.setattr(scan_service, "MAX_PATCH_CHARACTERS", 10)
    github_mock(response(pull_data), response([file_data]), response(pull_data))
    assert client.post("/scans", json=PAYLOAD).status_code == 422


def test_pending_running_completed_and_idempotent_execution(
    response, github_mock, pull_data, file_data, monkeypatch
):
    pending = scan_service.create_pending_scan(**PAYLOAD)
    assert scan_service.get_scan(pending.id).status == "pending"
    original = analyzer_service.analyze_changed_files

    def inspect_running(files):
        assert scan_service.get_scan(pending.id).status == "running"
        return original(files)

    monkeypatch.setattr(analyzer_service, "analyze_changed_files", inspect_running)
    mock = github_mock(response(pull_data), response([file_data]), response(pull_data))
    completed = scan_service.execute_scan(pending.id)
    assert completed.status == "completed"
    assert scan_service.execute_scan(pending.id) == completed
    assert mock.call_count == 3


def test_storage_copies_and_unique_ids_under_concurrency():
    with ThreadPoolExecutor(max_workers=8) as pool:
        scans = list(pool.map(lambda _: scan_service.create_pending_scan(**PAYLOAD), range(50)))
    assert len({scan.id for scan in scans}) == 50
    scan = scans[0]
    scan.status = "failed"
    scan.analysis_warnings.append("external mutation")
    assert scan_service.get_scan(scan.id).status == "pending"
    assert scan_service.get_scan(scan.id).analysis_warnings == []
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda _: scan_service.store.claim(scan.id)[1], range(50)))
    assert sum(claims) == 1


def test_storage_capacity(monkeypatch):
    monkeypatch.setattr(scan_service, "store", MemoryScanStore(max_scans=1))
    scan_service.create_pending_scan(**PAYLOAD)
    with pytest.raises(ServiceError, match="storage is full"):
        scan_service.create_pending_scan(**PAYLOAD)
