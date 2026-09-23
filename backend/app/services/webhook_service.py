"""Authenticate the raw body, deduplicate, then durably enqueue work."""

import hashlib
import hmac
import json
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core import context
from app.core.config import get_settings
from app.core.errors import ServiceError
from app.db.session import session_scope
from app.models import GitHubInstallation, WebhookDelivery
from app.services import github_service, job_service, scan_service

MAX_BODY = 1_048_576
PR_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


def verify_signature(body: bytes, signature: str):
    secret = get_settings().github_webhook_secret
    if not secret:
        raise ServiceError("GitHub webhook is not configured.", 503)
    expected = (
        "sha256=" + hmac.new(secret.get_secret_value().encode(), body, hashlib.sha256).hexdigest()
    )
    if not re.fullmatch(r"sha256=[0-9a-f]{64}", signature) or not hmac.compare_digest(
        expected, signature
    ):
        raise ServiceError("Invalid webhook signature.", 401)


def receive(body: bytes, signature: str, event: str, delivery_id: str):
    if len(body) > MAX_BODY:
        raise ServiceError("Webhook body exceeds the size limit.", 413)
    verify_signature(body, signature)
    if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", delivery_id):
        raise ServiceError("Invalid webhook delivery ID.", 400)
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        raise ServiceError("Invalid webhook body.", 400) from None
    try:
        result = _accept(payload, event, delivery_id)
    except IntegrityError:
        # A concurrent delivery won the unique delivery/commit key; resolve it safely.
        result = _accept(payload, event, delivery_id)
    if result.get("scan_id"):
        job_service.dispatch(result["scan_id"])
    return result


def _accept(payload: dict, event: str, delivery_id: str):
    remote_id = (payload.get("installation") or {}).get("id")
    with session_scope() as session:
        prior = session.get(WebhookDelivery, delivery_id)
        if prior:
            return {"status": "duplicate", "scan_id": prior.scan_id}
        installation = session.scalar(
            select(GitHubInstallation).where(GitHubInstallation.github_installation_id == remote_id)
        )
        if event == "installation" and installation:
            if payload.get("action") in {"deleted", "suspend"}:
                installation.active = False
                with github_service._token_lock:
                    github_service._token_cache.pop(remote_id, None)
            # Unsuspension is re-verified through the connection flow.
        if (
            event != "pull_request"
            or payload.get("action") not in PR_ACTIONS
            or not installation
            or not installation.active
            or (get_settings().auth_enabled and installation.organization_id is None)
            or (payload.get("pull_request") or {}).get("draft")
        ):
            return {"status": "ignored"}
        try:
            repository = payload["repository"]
            pull = payload["pull_request"]
            full_name = repository["full_name"]
            owner, name = github_service.parse_github_url(f"https://github.com/{full_name}")
            number, sha = pull["number"], pull["head"]["sha"]
            if (
                full_name.lower() != f"{owner}/{name}".lower()
                or owner.lower() != installation.account_login.lower()
                or not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
                or not re.fullmatch(r"[0-9a-f]{40,64}", sha)
                or not isinstance(repository["id"], int)
            ):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ServiceError("Invalid pull request webhook.", 400) from None
        dedup = hashlib.sha256(
            f"{remote_id}:{repository['id']}:{number}:{sha}".encode()
        ).hexdigest()
        prior = session.scalar(select(WebhookDelivery).where(WebhookDelivery.dedup_key == dedup))
        if prior:
            return {"status": "duplicate", "scan_id": prior.scan_id}
        with context.organization_scope(installation.organization_id):
            scan = scan_service.create_pending_scan(
                f"https://github.com/{owner}/{name}",
                number,
                "webhook",
                expected_head_sha=sha,
                session=session,
            )
        session.add(
            WebhookDelivery(delivery_id=delivery_id, dedup_key=dedup, event=event, scan_id=scan.id)
        )
        return {"status": "accepted", "scan_id": scan.id}
