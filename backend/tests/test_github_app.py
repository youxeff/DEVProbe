import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import func, select

from app.core import context
from app.core.config import Settings
from app.core.errors import ServiceError
from app.db.scan_store import SQLScanStore
from app.db.session import session_scope
from app.models import GitHubCheck, GitHubInstallation, Scan, WebhookDelivery
from app.services import (
    github_service,
    integration_service,
    job_service,
    scan_service,
    webhook_service,
)

SECRET = "test-webhook-secret"


def signed(payload):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


@pytest.fixture
def app_setup(monkeypatch):
    settings = Settings(github_app_id="123", github_webhook_secret=SECRET)
    monkeypatch.setattr(webhook_service, "get_settings", lambda: settings)
    monkeypatch.setattr(github_service, "get_settings", lambda: settings)
    monkeypatch.setattr(scan_service, "store", SQLScanStore())
    monkeypatch.setattr(job_service, "dispatch", Mock(return_value=True))
    github_service._token_cache.clear()
    with session_scope() as session:
        session.add(
            GitHubInstallation(
                github_installation_id=456,
                account_login="owner",
                account_type="User",
                organization_id=None,
            )
        )
    return {
        "action": "opened",
        "installation": {"id": 456},
        "repository": {"id": 42, "full_name": "owner/repo"},
        "pull_request": {"number": 12, "draft": False, "head": {"sha": "a" * 40}},
    }


def test_jwt_is_rs256_and_short_lived(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    monkeypatch.setattr(
        github_service,
        "get_settings",
        lambda: Settings(github_app_id="123", github_private_key=pem),
    )
    claims = jwt.decode(github_service.app_jwt(), key.public_key(), algorithms=["RS256"])
    assert claims["iss"] == "123" and claims["exp"] - claims["iat"] == 600


def test_installation_tokens_cached_but_not_persisted(app_setup, monkeypatch):
    expires = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
    request = Mock(return_value=({"token": "installation-secret", "expires_at": expires}, None))
    monkeypatch.setattr(github_service, "app_request", request)
    monkeypatch.setattr(github_service, "app_jwt", lambda: "jwt")
    assert github_service.installation_token(456) == "installation-secret"
    assert github_service.installation_token(456) == "installation-secret"
    assert request.call_count == 1
    with context.organization_scope(999):
        assert "Authorization" not in github_service.github_headers()
    assert not any("token" in name for name in GitHubInstallation.__table__.columns.keys())


def test_signature_and_delivery_deduplication(client, app_setup):
    body, signature = signed(app_setup)
    headers = {
        "x-hub-signature-256": signature,
        "x-github-event": "pull_request",
        "x-github-delivery": "delivery-1",
    }
    assert client.post("/webhooks/github", content=body).status_code == 401
    accepted = client.post("/webhooks/github", content=body, headers=headers)
    assert accepted.status_code == 202 and accepted.json()["status"] == "accepted"
    repeated = client.post("/webhooks/github", content=body, headers=headers).json()
    assert repeated == {"status": "duplicate", "scan_id": 1}
    headers["x-github-delivery"] = "delivery-2"
    assert (
        client.post("/webhooks/github", content=body, headers=headers).json()["status"]
        == "duplicate"
    )
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(Scan)) == 1
        assert session.scalar(select(func.count()).select_from(WebhookDelivery)) == 1
        scan = session.get(Scan, 1)
        assert scan.status == "pending" and scan.expected_head_sha == "a" * 40
    assert b"test-webhook-secret" not in accepted.content


def test_altered_body_unknown_installation_and_revocation(client, app_setup):
    body, signature = signed(app_setup)
    with pytest.raises(ServiceError, match="signature"):
        webhook_service.receive(body + b" ", signature, "pull_request", "x")
    app_setup["installation"]["id"] = 999
    assert webhook_service.receive(*signed(app_setup), "pull_request", "x")["status"] == "ignored"
    revoked = {"action": "deleted", "installation": {"id": 456}}
    assert webhook_service.receive(*signed(revoked), "installation", "y")["status"] == "ignored"
    app_setup["installation"]["id"] = 456
    assert webhook_service.receive(*signed(app_setup), "pull_request", "z")["status"] == "ignored"


def test_webhook_rejects_wrong_owner_or_huge_body(app_setup):
    app_setup["repository"]["full_name"] = "another/repo"
    with pytest.raises(ServiceError, match="Invalid pull request"):
        webhook_service.receive(*signed(app_setup), "pull_request", "x")
    with pytest.raises(ServiceError) as error:
        webhook_service.receive(b"x" * (webhook_service.MAX_BODY + 1), "", "", "")
    assert error.value.status_code == 413


def test_stale_webhook_commit_fails_without_analyzing(
    app_setup, github_mock, response, pull_data, monkeypatch
):
    monkeypatch.setattr(github_service, "installation_token", lambda _: "token")
    webhook_service.receive(*signed(app_setup), "pull_request", "x")
    github_mock(response({**pull_data, "head": {"sha": "c" * 40}}))
    with pytest.raises(ServiceError, match="no longer the PR head"):
        scan_service.execute_scan(1)
    assert scan_service.get_scan(1).status == "failed"


def test_cannot_claim_someone_elses_installation(app_setup, monkeypatch):
    monkeypatch.setattr(github_service, "app_jwt", lambda: "jwt")
    monkeypatch.setattr(
        github_service,
        "app_request",
        Mock(
            side_effect=[
                ({"id": 2}, None),
                ({"account": {"id": 1, "login": "owner", "type": "User"}}, None),
            ]
        ),
    )
    with pytest.raises(ServiceError, match="owner access"):
        integration_service.link_installation(17, 456, "oauth-token")


def test_installation_cannot_move_between_tenants(app_setup, monkeypatch):
    monkeypatch.setattr(
        github_service,
        "verify_installation_owner",
        lambda *args: {
            "github_installation_id": 456,
            "account_login": "owner",
            "account_type": "User",
            "active": True,
        },
    )
    with pytest.raises(ServiceError, match="another organization"):
        integration_service.link_installation(17, 456, "oauth-token")


def test_check_reuses_commit_record_and_sends_no_source(app_setup, monkeypatch):
    scan = scan_service.create_pending_scan("https://github.com/owner/repo", 12)
    scan.status, scan.head_sha, scan.risk_score, scan.risk_level = "completed", "a" * 40, 16, "Low"
    scan_service.store.save(scan)
    publish = Mock(return_value=99)
    monkeypatch.setattr(github_service, "publish_check", publish)
    assert integration_service.publish_scan(scan) == {"check_run_id": 99}
    assert integration_service.publish_scan(scan) == {"check_run_id": 99}
    assert publish.call_args.args[-1] == 99
    assert publish.call_args.args[-2]["conclusion"] == "neutral"
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(GitHubCheck)) == 1


def test_remote_check_recovery_updates_instead_of_duplicating(app_setup, monkeypatch):
    monkeypatch.setattr(github_service, "installation_token", lambda _: "token")
    request = Mock(
        side_effect=[
            ({"check_runs": [{"id": 77, "external_id": "stable", "app": {"id": 123}}]}, None),
            ({"id": 77}, None),
        ]
    )
    monkeypatch.setattr(github_service, "app_request", request)
    with integration_service.repository_credentials("https://github.com/owner/repo", None):
        result = github_service.publish_check(
            "https://github.com/owner/repo",
            "a" * 40,
            "stable",
            {"conclusion": "neutral", "title": "risk", "summary": "counts"},
        )
    assert result == 77
    assert [call.args[0] for call in request.call_args_list] == ["GET", "PATCH"]
