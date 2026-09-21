import hmac
import logging
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import context
from app.core.config import get_settings
from app.core.errors import ServiceError
from app.core.security import digest
from app.services import auth_service

logger = logging.getLogger("devprobe.requests")
PUBLIC = {
    "/health",
    "/health/ready",
    "/auth/session",
    "/auth/login",
    "/auth/register",
    "/webhooks/github",
    "/webhooks/stripe",
}
SIGNED_WEBHOOKS = {"/webhooks/github", "/webhooks/stripe"}


class IdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started, request_id = perf_counter(), uuid4().hex
        settings = get_settings()
        tokens = []
        request.state.identity = None
        try:
            if settings.auth_enabled and request.url.path not in SIGNED_WEBHOOKS:
                identity = await run_in_threadpool(
                    auth_service.identity,
                    request.cookies.get("dp_session"),
                    request.headers.get("x-organization-id"),
                )
                request.state.identity = identity
                if request.url.path not in PUBLIC and identity is None:
                    raise ServiceError("Sign in to continue.", 401)
                if identity:
                    active = identity["active_organization"]
                    allowed_without_org = (
                        request.url.path in PUBLIC
                        or request.url.path.startswith("/auth/")
                        or (
                            request.method == "POST"
                            and request.url.path
                            in {"/organizations", "/organizations/invitations/accept"}
                        )
                    )
                    if active is None and not allowed_without_org:
                        raise ServiceError("Organization membership is required.", 403)
                    for variable, value in (
                        (context.user_id, identity["user"]["id"]),
                        (context.organization_id, active["id"] if active else None),
                        (context.role, active["role"] if active else None),
                    ):
                        tokens.append((variable, variable.set(value)))
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    public = urlsplit(settings.public_url)
                    expected_origin = f"{public.scheme}://{public.netloc}"
                    if request.headers.get("origin") != expected_origin:
                        raise ServiceError("Request origin is not allowed.", 403)
                    if request.url.path not in {"/auth/login", "/auth/register"}:
                        csrf = request.headers.get("x-csrf-token", "")
                        if not identity or not hmac.compare_digest(
                            digest(csrf), identity["csrf_hash"]
                        ):
                            raise ServiceError("Refresh your session and try again.", 403)
            response = await call_next(request)
        except ServiceError as error:
            response = JSONResponse(
                {"detail": error.message}, status_code=error.status_code, headers=error.headers
            )
        finally:
            organization = context.organization_id.get()
            for variable, token in reversed(tokens):
                variable.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        route = request.scope.get("route")
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "organization_id": organization,
                "status": response.status_code,
                "duration_seconds": round(perf_counter() - started, 6),
            },
        )
        return response
