from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import urlsplit

import pytest
from sqlalchemy import select

from app.core import config, context
from app.db.session import session_scope
from app.models import AuditLog, UsageCounter, User, UserSession
from app.services import scan_service, usage_service

ORIGIN = "http://localhost:3000"
PASSWORD = "fixture-only-long-password"


def register(client, email="owner@example.com"):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Test User",
            "organization_name": email.split("@")[0],
        },
    )
    assert response.status_code == 201, response.text
    client.headers["x-csrf-token"] = client.cookies.get("dp_csrf")
    return client.get("/auth/session").json()


def test_session_password_and_cookie_security(auth_client):
    assert auth_client.get("/scans").status_code == 401
    assert (
        auth_client.post(
            "/repo/pulls", json={"repo_url": "https://github.com/owner/repo"}
        ).status_code
        == 401
    )
    identity = register(auth_client)
    assert identity["active_organization"]["role"] == "owner"
    assert "csrf_hash" not in identity
    with session_scope() as session:
        user = session.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$") and PASSWORD not in user.password_hash
        saved = session.scalar(select(UserSession))
        assert saved.token_hash != auth_client.cookies.get("dp_session")
    old = auth_client.cookies.get("dp_session")
    assert auth_client.post("/auth/logout").status_code == 200
    auth_client.cookies.set("dp_session", old)
    assert auth_client.get("/scans").status_code == 401
    auth_client.cookies.clear()
    response = auth_client.post(
        "/auth/login", json={"email": "owner@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers.get_list("set-cookie")[0]
    assert auth_client.cookies.get("dp_session") != old


def test_csrf_and_origin(auth_client):
    register(auth_client)
    assert (
        auth_client.post(
            "/organizations", json={"name": "new"}, headers={"x-csrf-token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        auth_client.post(
            "/organizations", json={"name": "new"}, headers={"origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert auth_client.post("/organizations", json={"name": "new"}).status_code == 201


def test_tenant_isolation_in_objects_lists_analytics_and_legacy(
    auth_client, monkeypatch, response, github_mock, repository_data, pull_data, file_data
):
    owner = register(auth_client)
    github_mock(response(repository_data), response([]))
    repo = auth_client.post(
        "/repo/metadata", json={"repo_url": "https://github.com/owner/repo"}
    ).json()
    github_mock(response(pull_data), response([file_data]), response(pull_data))
    created = auth_client.post("/scans", json={"repo_url": repo["html_url"], "pr_number": 12})
    assert created.status_code == 200, created.text
    assert (
        auth_client.get("/scans/1").json()["organization_id"] == owner["active_organization"]["id"]
    )
    second = auth_client.post("/organizations", json={"name": "Separate"}).json()
    auth_client.headers["x-organization-id"] = str(second["id"])
    assert auth_client.get(f"/repositories/{repo['id']}").status_code == 404
    assert auth_client.get(f"/repositories/{repo['id']}/scans").status_code == 404
    assert auth_client.get("/scans/1").status_code == 404
    assert auth_client.get("/scans").json()["total"] == 0
    assert auth_client.get("/analytics").json()["total_scans"] == 0
    assert auth_client.get("/repositories").json() == []
    auth_client.headers["x-organization-id"] = "999"
    assert auth_client.get("/scans/1").status_code == 404


def test_invitation_roles_last_owner_and_audit(auth_client):
    owner = register(auth_client)
    org = owner["active_organization"]["id"]
    invited = auth_client.post(
        "/organizations/invitations", json={"email": "viewer@example.com", "role": "viewer"}
    )
    token = urlsplit(invited.json()["invite_url"]).fragment
    owner_cookies = dict(auth_client.cookies)
    auth_client.post("/auth/logout")
    register(auth_client, "viewer@example.com")
    assert (
        auth_client.post("/organizations/invitations/accept", json={"token": token}).status_code
        == 200
    )
    assert (
        auth_client.post("/organizations/invitations/accept", json={"token": token}).status_code
        == 404
    )
    auth_client.headers["x-organization-id"] = str(org)
    assert auth_client.get("/repositories").status_code == 200
    assert (
        auth_client.post(
            "/scans", json={"repo_url": "https://github.com/owner/repo", "pr_number": 12}
        ).status_code
        == 403
    )
    assert (
        auth_client.post(
            "/repo/metadata", json={"repo_url": "https://github.com/owner/repo"}
        ).status_code
        == 403
    )
    assert (
        auth_client.post(
            "/organizations/invitations", json={"email": "more@example.com"}
        ).status_code
        == 403
    )
    # Owner signs back in; revoked sessions cannot be reused.
    auth_client.headers.pop("x-organization-id")
    auth_client.post("/auth/login", json={"email": "owner@example.com", "password": PASSWORD})
    auth_client.headers["x-csrf-token"] = auth_client.cookies.get("dp_csrf")
    members = auth_client.get("/organizations/members").json()
    owner_id = next(m["id"] for m in members if m["role"] == "owner")
    viewer_id = next(m["id"] for m in members if m["role"] == "viewer")
    assert auth_client.delete(f"/organizations/members/{owner_id}").status_code == 409
    assert (
        auth_client.patch(
            f"/organizations/members/{viewer_id}", json={"role": "member"}
        ).status_code
        == 200
    )
    assert auth_client.get("/organizations/audit").status_code == 200
    with session_scope() as session:
        events = [row.action for row in session.scalars(select(AuditLog))]
        assert "invitation.accepted" in events and "membership.updated" in events
    assert owner_cookies["dp_session"] != auth_client.cookies.get("dp_session")


def test_scan_limits_are_atomic_and_rollback_when_rejected(auth_client, monkeypatch):
    identity = register(auth_client)
    org = identity["active_organization"]["id"]
    monkeypatch.setitem(usage_service.LIMITS, "free", {"scans": 3, "repositories": 5, "members": 3})

    def create(_):
        with context.organization_scope(org):
            try:
                return scan_service.create_pending_scan("https://github.com/owner/repo", 12).id
            except Exception as error:
                return getattr(error, "status_code", None)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(create, range(8)))
    assert results.count(429) == 5, results
    assert auth_client.get("/organizations/usage").json()["scans"] == 3
    with session_scope() as session:
        assert session.scalar(select(UsageCounter.scans)) == 3


def test_auth_throttling_and_production_guard(auth_client):
    for _ in range(10):
        result = auth_client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
        )
        assert result.status_code == 401
    result = auth_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert result.status_code == 429 and result.headers["retry-after"] == "600"
    with pytest.raises(ValueError):
        config.Settings(app_env="production")
    valid = config.Settings(
        app_env="production",
        auth_enabled=True,
        public_url="https://devprobe.example",
        database_url="postgresql://user:pass@db/devprobe",
    )
    assert valid.auth_enabled
    with pytest.raises(ValueError) as failure:
        config.Settings(app_env="production", github_token="must-not-appear-in-errors")
    assert "must-not-appear-in-errors" not in str(failure.value)


def test_session_expiry_and_password_change(auth_client):
    register(auth_client)
    assert (
        auth_client.post(
            "/auth/password",
            json={"current_password": PASSWORD, "new_password": "different-fixture-password"},
        ).status_code
        == 200
    )
    assert auth_client.get("/repositories").status_code == 401
    auth_client.post(
        "/auth/login", json={"email": "owner@example.com", "password": "different-fixture-password"}
    )
    with session_scope() as session:
        saved = session.scalar(select(UserSession))
        saved.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
    assert auth_client.get("/repositories").status_code == 401


def test_legacy_rows_are_not_adopted_and_no_membership_cannot_read_them(auth_client):
    from sqlalchemy import delete

    from app.models import Membership

    legacy = scan_service.create_pending_scan("https://github.com/owner/repo", 12)
    identity = register(auth_client)
    assert auth_client.get(f"/scans/{legacy.id}").status_code == 404
    assert auth_client.get("/scans").json()["total"] == 0
    with session_scope() as session:
        session.execute(delete(Membership).where(Membership.user_id == identity["user"]["id"]))
    assert auth_client.get(f"/scans/{legacy.id}").status_code == 403
    assert auth_client.post("/organizations", json={"name": "New workspace"}).status_code == 201
    assert auth_client.get(f"/scans/{legacy.id}").status_code == 404
