import hashlib
import secrets

from app.core import context
from app.core.config import get_settings
from app.core.errors import ServiceError

ROLE_LEVEL = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def require_role(minimum="member"):
    if not get_settings().auth_enabled:
        return
    if context.user_id.get() is None:
        raise ServiceError("Sign in to continue.", 401)
    if ROLE_LEVEL.get(context.role.get(), -1) < ROLE_LEVEL[minimum]:
        raise ServiceError("Your organization role does not allow this action.", 403)


def require_identity():
    if context.user_id.get() is None or context.organization_id.get() is None:
        raise ServiceError("Sign in with an organization to use this feature.", 401)
    return context.user_id.get(), context.organization_id.get()


def require_user():
    if context.user_id.get() is None:
        raise ServiceError("Sign in to continue.", 401)
    return context.user_id.get()
