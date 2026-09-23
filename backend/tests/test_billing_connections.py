import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.session import session_scope
from app.models import BillingEvent, GitHubInstallation, GitHubOAuthState
from app.services import billing_service, github_service
from tests.test_auth_tenants import register


@pytest.fixture
def providers(monkeypatch):
    settings = Settings(
        auth_enabled=True,
        github_app_id="123",
        github_client_id="app-client",
        github_client_secret="app-secret",
        github_private_key="not-used-in-mock",
        github_app_slug="devprobe",
        stripe_secret_key="sk_test_fixture",
        stripe_pro_price_id="price_pro",
        stripe_webhook_secret="whsec_fixture",
    )
    monkeypatch.setattr(billing_service, "get_settings", lambda: settings)
    import app.core.config as config

    # Integration service imports configuration at call time.
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "app-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "app-secret")
    monkeypatch.setenv("GITHUB_PRIVATE_KEY", "not-used-in-mock")
    config.get_settings.cache_clear()
    client = MagicMock()
    client.v1.customers.create.return_value = {"id": "cus_fixture"}
    client.v1.subscriptions.list.return_value = {"data": [], "has_more": False}
    client.v1.checkout.sessions.create.return_value = {
        "id": "cs_fixture",
        "url": "https://checkout.stripe.com/c/pay/fixture",
        "expires_at": int(time.time()) + 3600,
    }
    client.v1.checkout.sessions.retrieve.return_value = {
        "id": "cs_fixture",
        "status": "open",
        "url": "https://checkout.stripe.com/c/pay/fixture",
    }
    client.v1.billing_portal.sessions.create.return_value = {
        "url": "https://billing.stripe.com/p/fixture"
    }
    monkeypatch.setattr(billing_service, "_client", lambda: client)
    return client


def webhook(client, event_id="evt_1", event_type="customer.subscription.updated", *, old=False):
    body = json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "data": {"object": {"customer": "cus_fixture"}},
        }
    ).encode()
    timestamp = int(time.time()) - (600 if old else 0)
    signature = hmac.new(
        b"whsec_fixture", str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return client.post(
        "/webhooks/stripe",
        content=body,
        headers={"stripe-signature": f"t={timestamp},v1={signature}"},
    )


def test_checkout_reuse_and_plan_only_after_verified_provider_state(auth_client, providers):
    register(auth_client)
    assert (
        auth_client.post(
            "/billing/checkout", json={"plan": "pro", "price": "price_free"}
        ).status_code
        == 200
    )
    assert auth_client.post("/billing/checkout").status_code == 200
    assert providers.v1.checkout.sessions.create.call_count == 1
    assert (
        providers.v1.checkout.sessions.create.call_args.args[0]["line_items"][0]["price"]
        == "price_pro"
    )
    assert auth_client.get("/organizations/usage").json()["plan"] == "free"
    assert auth_client.post("/webhooks/stripe", content=b"{}").status_code == 401
    assert webhook(auth_client, old=True).status_code == 401
    providers.v1.subscriptions.list.return_value = {
        "data": [
            {
                "id": "sub_fixture",
                "created": 1,
                "status": "active",
                "items": {"data": [{"price": {"id": "price_pro"}}]},
            }
        ],
        "has_more": False,
    }
    assert webhook(auth_client).json()["status"] == "accepted"
    assert auth_client.get("/organizations/usage").json()["plan"] == "pro"
    assert webhook(auth_client).json()["status"] == "duplicate"
    # An old 'deleted' event still reconciles current active state.
    assert webhook(auth_client, "evt_2", "customer.subscription.deleted").status_code == 200
    assert auth_client.get("/organizations/usage").json()["plan"] == "pro"
    assert auth_client.post("/billing/checkout").status_code == 409
    assert (
        auth_client.post("/billing/portal").json()["url"].startswith("https://billing.stripe.com/")
    )
    providers.v1.subscriptions.list.return_value = {"data": [], "has_more": False}
    assert webhook(auth_client, "evt_3").status_code == 200
    assert auth_client.get("/organizations/usage").json()["plan"] == "free"
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(BillingEvent)) == 3


def test_billing_customer_is_tenant_scoped(auth_client, providers):
    register(auth_client)
    auth_client.post("/billing/checkout")
    other = auth_client.post("/organizations", json={"name": "other"}).json()
    auth_client.headers["x-organization-id"] = str(other["id"])
    assert auth_client.get("/billing").json()["has_customer"] is False
    assert auth_client.post("/billing/portal").status_code == 409


def test_oauth_state_is_one_time_user_bound_and_pkce(auth_client, providers, monkeypatch):
    owner = register(auth_client)
    result = auth_client.post("/github/connect", json={"installation_id": 456})
    assert result.status_code == 200, result.text
    params = parse_qs(urlsplit(result.json()["url"]).query)
    state = params["state"][0]
    assert params["code_challenge_method"] == ["S256"]
    with session_scope() as session:
        row = session.scalar(select(GitHubOAuthState))
        assert row.state_hash != state and row.code_verifier not in result.text
    exchange = MagicMock(return_value="ephemeral-user-token")
    monkeypatch.setattr(github_service, "exchange_oauth_code", exchange)
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
    assert (
        auth_client.get(
            "/github/callback", params={"code": "code", "state": "invalid-state-value-long"}
        ).status_code
        == 400
    )
    callback = auth_client.get(
        "/github/callback", params={"code": "code", "state": state}, follow_redirects=False
    )
    assert callback.status_code == 303, callback.text
    assert exchange.call_args.args[1] == row.code_verifier
    assert (
        auth_client.get(
            "/github/callback", params={"code": "code", "state": state}, follow_redirects=False
        ).status_code
        == 400
    )
    installations = auth_client.get("/github").json()["installations"]
    assert len(installations) == 1 and not installations[0]["publish_checks"]
    assert (
        auth_client.patch("/github/installations/1", json={"publish_checks": True}).status_code
        == 200
    )
    other = auth_client.post("/organizations", json={"name": "other"}).json()
    auth_client.headers["x-organization-id"] = str(other["id"])
    assert auth_client.get("/github").json()["installations"] == []
    assert auth_client.delete("/github/installations/1").status_code == 404
    auth_client.headers["x-organization-id"] = str(owner["active_organization"]["id"])
    assert auth_client.delete("/github/installations/1").status_code == 200
    with session_scope() as session:
        assert session.get(GitHubInstallation, 1).active is False


def test_oauth_callback_cannot_be_used_by_another_user(auth_client, providers):
    register(auth_client)
    params = parse_qs(
        urlsplit(
            auth_client.post("/github/connect", json={"installation_id": 456}).json()["url"]
        ).query
    )
    auth_client.post("/auth/logout")
    register(auth_client, "attacker@example.com")
    assert (
        auth_client.get(
            "/github/callback", params={"code": "code", "state": params["state"][0]}
        ).status_code
        == 400
    )
