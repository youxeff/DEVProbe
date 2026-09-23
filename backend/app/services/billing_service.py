"""Optional hosted billing. The provider, never a browser payload, determines the plan."""

from datetime import UTC, datetime
from urllib.parse import urlsplit

import stripe
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import ServiceError
from app.core.security import require_identity, require_role
from app.db.session import session_scope
from app.models import BillingEvent, Subscription
from app.services.auth_service import utc
from app.services.repository_service import upsert
from app.services.usage_service import audit, lock_organization


def configured():
    settings = get_settings()
    return bool(
        settings.stripe_secret_key
        and settings.stripe_pro_price_id
        and settings.stripe_webhook_secret
    )


def _client():
    if not configured():
        raise ServiceError("Billing is not configured.", 503)
    return stripe.StripeClient(
        get_settings().stripe_secret_key.get_secret_value(),
        max_network_retries=1,
        http_client=stripe.RequestsClient(timeout=10),
    )


def _safe_url(url, hostname):
    parsed = urlsplit(url or "")
    if parsed.scheme != "https" or parsed.netloc != hostname:
        raise ServiceError("Billing provider returned an invalid URL.", 502)
    return url


def _subscriptions(client, customer):
    result, after = [], None
    for _ in range(10):
        params = {"customer": customer, "status": "all", "limit": 100}
        if after:
            params["starting_after"] = after
        page = client.v1.subscriptions.list(params)
        if isinstance(page, stripe.StripeObject):
            page = page.to_dict()
        result.extend(page["data"])
        if not page.get("has_more"):
            return result
        after = page["data"][-1]["id"]
    raise ServiceError("Billing history exceeds the retrieval limit.", 502)


def _reconcile(client, org, subscription):
    rows = _subscriptions(client, subscription.stripe_customer_id)
    price = get_settings().stripe_pro_price_id
    relevant = [
        row
        for row in rows
        if any(
            item.get("price", {}).get("id") == price
            for item in row.get("items", {}).get("data", [])
        )
    ]
    entitled = [row for row in relevant if row["status"] in {"active", "trialing"}]
    active = entitled or [
        row for row in relevant if row["status"] not in {"canceled", "incomplete_expired"}
    ]
    current = max(active or relevant, key=lambda row: row.get("created", 0), default=None)
    org.plan = "pro" if entitled else "free"
    subscription.status = current["status"] if current else "none"
    subscription.stripe_subscription_id = current["id"] if current else None
    return bool(active)


def checkout():
    _, org_id = require_identity()
    require_role("owner")
    client, now = _client(), datetime.now(UTC)
    try:
        with session_scope() as session:
            org = lock_organization(session, org_id)
            subscription = upsert(
                session,
                Subscription,
                {"organization_id": org_id, "status": "none"},
                ["organization_id"],
                update=False,
            )
            if not subscription.stripe_customer_id:
                customer = client.v1.customers.create(
                    {"metadata": {"devprobe_organization_id": str(org_id)}},
                    {"idempotency_key": f"devprobe-customer-{org_id}"},
                )
                subscription.stripe_customer_id = customer["id"]
            if _reconcile(client, org, subscription):
                raise ServiceError("A subscription already exists. Use Manage billing.", 409)
            if (
                subscription.checkout_session_id
                and subscription.checkout_expires_at
                and utc(subscription.checkout_expires_at) > now
            ):
                existing = client.v1.checkout.sessions.retrieve(subscription.checkout_session_id)
                if existing["status"] == "open":
                    return {"url": _safe_url(existing["url"], "checkout.stripe.com")}
                if existing["status"] == "complete":
                    raise ServiceError("Payment is being confirmed. Refresh billing shortly.", 409)
            settings = get_settings()
            result = client.v1.checkout.sessions.create(
                {
                    "mode": "subscription",
                    "customer": subscription.stripe_customer_id,
                    "line_items": [{"price": settings.stripe_pro_price_id, "quantity": 1}],
                    "success_url": settings.public_url + "/settings?billing=returned",
                    "cancel_url": settings.public_url + "/settings",
                    "client_reference_id": str(org_id),
                },
                {
                    "idempotency_key": (
                        f"devprobe-checkout-{org_id}-{subscription.checkout_session_id or 'first'}"
                    )
                },
            )
            subscription.checkout_session_id = result["id"]
            subscription.checkout_url = _safe_url(result["url"], "checkout.stripe.com")
            subscription.checkout_expires_at = datetime.fromtimestamp(result["expires_at"], UTC)
            audit(session, org_id, "billing.checkout_created")
            return {"url": subscription.checkout_url}
    except stripe.StripeError:
        raise ServiceError("Billing provider could not complete this request.", 502) from None


def portal():
    _, org_id = require_identity()
    require_role("owner")
    client = _client()
    with session_scope() as session:
        subscription = session.get(Subscription, org_id)
        if not subscription or not subscription.stripe_customer_id:
            raise ServiceError("No billing account exists yet.", 409)
        try:
            result = client.v1.billing_portal.sessions.create(
                {
                    "customer": subscription.stripe_customer_id,
                    "return_url": get_settings().public_url + "/settings",
                }
            )
        except stripe.StripeError:
            raise ServiceError("Billing provider could not complete this request.", 502) from None
        audit(session, org_id, "billing.portal_opened")
        return {"url": _safe_url(result["url"], "billing.stripe.com")}


def status():
    _, org_id = require_identity()
    with session_scope() as session:
        subscription = session.get(Subscription, org_id)
        return {
            "configured": configured(),
            "status": subscription.status if subscription else "none",
            "has_customer": bool(subscription and subscription.stripe_customer_id),
        }


def webhook(body, signature):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise ServiceError("Billing webhook is not configured.", 503)
    if len(body) > 1_048_576:
        raise ServiceError("Webhook body exceeds the size limit.", 413)
    try:
        event = stripe.Webhook.construct_event(
            body, signature, settings.stripe_webhook_secret.get_secret_value(), tolerance=300
        ).to_dict()
    except (ValueError, stripe.SignatureVerificationError):
        raise ServiceError("Invalid billing webhook signature.", 401) from None
    if event["type"] not in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        return {"status": "ignored"}
    customer = event["data"]["object"].get("customer")
    try:
        with session_scope() as session:
            subscription = session.scalar(
                select(Subscription).where(Subscription.stripe_customer_id == customer)
            )
            if not subscription:
                return {"status": "ignored"}
            org = lock_organization(session, subscription.organization_id)
            if session.get(BillingEvent, event["id"]):
                return {"status": "duplicate"}
            # Serialize fresh provider reads so old events cannot roll back the plan.
            _reconcile(_client(), org, subscription)
            session.add(BillingEvent(event_id=event["id"]))
            audit(session, org.id, "billing.subscription_reconciled")
            return {"status": "accepted"}
    except stripe.StripeError:
        raise ServiceError("Billing state could not be refreshed. Retry delivery.", 503) from None
