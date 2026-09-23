"""Password verification, opaque revocable sessions, and database-backed login throttling."""

from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import case, delete, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.errors import ServiceError
from app.core.security import digest, new_token
from app.db.session import session_scope
from app.models import AuthRateLimit, Membership, Organization, User, UserSession
from app.services.repository_service import upsert

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_dummy_hash = _hasher.hash(new_token())


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def throttle(key: str, *, limit=10, seconds=600):
    now = datetime.now(UTC)
    with session_scope() as session:
        session.execute(
            delete(AuthRateLimit).where(AuthRateLimit.expires_at < now - timedelta(days=1))
        )
        row = upsert(
            session,
            AuthRateLimit,
            {
                "key": digest(key),
                "count": 0,
                "expires_at": now + timedelta(seconds=seconds),
            },
            ["key"],
            update=False,
        )
        session.execute(
            update(AuthRateLimit)
            .where(AuthRateLimit.key == row.key)
            .values(
                count=case((AuthRateLimit.expires_at < now, 1), else_=AuthRateLimit.count + 1),
                expires_at=case(
                    (AuthRateLimit.expires_at < now, now + timedelta(seconds=seconds)),
                    else_=AuthRateLimit.expires_at,
                ),
            )
        )
        session.refresh(row)
        exceeded = row.count > limit
    if exceeded:
        raise ServiceError(
            "Too many attempts. Try again later.", 429, {"Retry-After": str(seconds)}
        )


def _enabled():
    if not get_settings().auth_enabled:
        raise ServiceError("Authentication is disabled in local development mode.", 409)


def _session(session, user_id):
    token, csrf = new_token(), new_token()
    now = datetime.now(UTC)
    session.execute(delete(UserSession).where(UserSession.expires_at < now))
    session.add(
        UserSession(
            token_hash=digest(token),
            user_id=user_id,
            csrf_hash=digest(csrf),
            expires_at=now + timedelta(seconds=get_settings().session_ttl_seconds),
        )
    )
    return token, csrf


def register(payload, ip: str):
    _enabled()
    if not get_settings().registration_enabled:
        raise ServiceError("Registration is closed. Contact the operator.", 403)
    throttle("register:" + ip, limit=10, seconds=3600)
    hashed = _hasher.hash(payload.password)
    try:
        with session_scope() as session:
            user = User(
                email=str(payload.email).lower(), name=payload.name.strip(), password_hash=hashed
            )
            organization = Organization(name=payload.organization_name.strip())
            session.add_all([user, organization])
            session.flush()
            session.add(Membership(user_id=user.id, organization_id=organization.id, role="owner"))
            from app.services.usage_service import audit

            audit(
                session, organization.id, "organization.created", organization.id, user_id=user.id
            )
            return _session(session, user.id)
    except IntegrityError:
        raise ServiceError("This account could not be created. Try signing in.", 409) from None


def login(payload, ip: str):
    _enabled()
    email = str(payload.email).lower()
    throttle("login-ip:" + ip, limit=100, seconds=3600)
    throttle("login-account:" + email)
    with session_scope() as session:
        user = session.scalar(select(User).where(User.email == email))
        try:
            _hasher.verify(user.password_hash if user else _dummy_hash, payload.password)
        except (VerificationError, InvalidHashError):
            raise ServiceError("Email or password is incorrect.", 401) from None
        if user is None:
            raise ServiceError("Email or password is incorrect.", 401)
        if _hasher.check_needs_rehash(user.password_hash):
            user.password_hash = _hasher.hash(payload.password)
        return _session(session, user.id)


def identity(token: str | None, requested_org: str | None = None):
    if not token or len(token) > 200:
        return None
    with session_scope() as session:
        saved = session.get(UserSession, digest(token))
        if not saved or utc(saved.expires_at) <= datetime.now(UTC):
            return None
        user = session.get(User, saved.user_id)
        memberships = session.execute(
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(Membership.user_id == user.id)
            .order_by(Organization.id)
        ).all()
        organizations = [
            {"id": org.id, "name": org.name, "plan": org.plan, "role": member.role}
            for member, org in memberships
        ]
        active = next((org for org in organizations if str(org["id"]) == requested_org), None)
        if requested_org and active is None:
            raise ServiceError("Organization not found.", 404)
        active = active or (organizations[0] if organizations else None)
        return {
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "organizations": organizations,
            "active_organization": active,
            "csrf_hash": saved.csrf_hash,
        }


def logout(token: str | None):
    if token:
        with session_scope() as session:
            session.execute(delete(UserSession).where(UserSession.token_hash == digest(token)))


def change_password(user_id: int, payload):
    with session_scope() as session:
        user = session.get(User, user_id)
        try:
            _hasher.verify(user.password_hash, payload.current_password)
        except (VerificationError, InvalidHashError):
            raise ServiceError("Current password is incorrect.", 400) from None
        user.password_hash = _hasher.hash(payload.new_password)
        session.execute(delete(UserSession).where(UserSession.user_id == user_id))
