from app.db.scan_store import SQLScanStore
from app.services import scan_service


def test_metrics_and_paginated_history(
    client, monkeypatch, response, github_mock, pull_data, file_data
):
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    github_mock(response(pull_data), response([file_data]), response(pull_data), response({}, 404))
    payload = {"repo_url": "https://github.com/owner/repo", "pr_number": 12}
    assert client.post("/scans", json=payload).status_code == 200
    assert client.post("/scans", json=payload).status_code == 404
    scan_service.create_pending_scan(**payload)
    summary = client.get("/analytics").json()
    assert (
        summary["total_scans"] == 3
        and summary["completed_scans"] == 1
        and summary["failed_scans"] == 1
    )
    assert summary["prs_analyzed"] == 1 and summary["average_risk_score"] == 6
    assert summary["total_issues"] == 3
    assert summary["severity_counts"] == {"low": 2, "medium": 1}
    assert summary["failure_rate"] == 1 / 3
    page = client.get("/scans?offset=1&limit=1").json()
    assert page["total"] == 3 and len(page["items"]) == 1 and page["items"][0]["status"] == "failed"
    assert len(summary["trend"]) == 1


def test_empty_metrics_have_no_fabricated_averages(client):
    result = client.get("/analytics").json()
    assert result["total_scans"] == 0
    assert result["average_risk_score"] is None
    assert result["ai_estimated_cost"] is None
    assert client.get("/scans?limit=100000").status_code == 422
