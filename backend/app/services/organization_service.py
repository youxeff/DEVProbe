from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update

from app.core import context
from app.core.config import get_settings
from app.core.errors import ServiceError
from app.core.security import digest, new_token, require_identity, require_role, require_user
from app.db.session import session_scope
from app.models import AuditLog, Invitation, Membership, Organization, User
from app.services.auth_service import utc
from app.services.usage_service import LIMITS, audit, lock_organization


def create(name):
    user = require_user()
    with session_scope() as session:
        session.execute(update(User).where(User.id == user).values(updated_at=datetime.now(UTC)))
        owned = session.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.user_id == user, Membership.role == "owner")
        )
        if owned >= 10:
            raise ServiceError("Organization creation limit reached.", 429)
        org = Organization(name=name.strip())
        session.add(org)
        session.flush()
        session.add(Membership(user_id=user, organization_id=org.id, role="owner"))
        audit(session, org.id, "organization.created", org.id)
        return {"id": org.id, "name": org.name, "plan": org.plan, "role": "owner"}


def members():
    _, org = require_identity()
    with session_scope() as session:
        rows = session.execute(
            select(Membership, User)
            .join(User)
            .where(Membership.organization_id == org)
            .order_by(Membership.id)
        ).all()
        return [
            {
                "id": member.id,
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": member.role,
            }
            for member, user in rows
        ]


def invite(email, role):
    _, org_id = require_identity()
    require_role("admin")
    token, now = new_token(), datetime.now(UTC)
    with session_scope() as session:
        org = lock_organization(session, org_id)
        email = email.lower()
        session.execute(
            delete(Invitation).where(
                Invitation.organization_id == org_id, Invitation.email == email
            )
        )
        members_count = session.scalar(
            select(func.count()).select_from(Membership).where(Membership.organization_id == org_id)
        )
        invites = session.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(Invitation.organization_id == org_id, Invitation.expires_at > now)
        )
        if members_count + invites >= LIMITS[org.plan]["members"]:
            raise ServiceError("Member limit reached for this plan.", 429)
        session.add(
            Invitation(
                token_hash=digest(token),
                organization_id=org_id,
                email=email,
                role=role,
                expires_at=now + timedelta(days=2),
            )
        )
        audit(session, org_id, "invitation.created")
    # The administrator delivers this link; the application sends no email.
    return {
        "invite_url": get_settings().public_url + "/invite#" + token,
        "expires_in_seconds": 172800,
    }


def accept(token):
    user_id = require_user()
    with session_scope() as session:
        invitation = session.get(Invitation, digest(token))
        user = session.get(User, user_id)
        if (
            not invitation
            or utc(invitation.expires_at) <= datetime.now(UTC)
            or invitation.email != user.email
        ):
            raise ServiceError("Invitation is invalid or expired for this account.", 404)
        org = lock_organization(session, invitation.organization_id)
        # Re-read after acquiring the organization lock to prevent token replay races.
        invitation = session.scalar(
            select(Invitation).where(Invitation.token_hash == digest(token))
        )
        if invitation is None:
            raise ServiceError("Invitation was already used.", 404)
        existing = session.scalar(
            select(Membership).where(
                Membership.organization_id == org.id, Membership.user_id == user_id
            )
        )
        if existing is None:
            count = session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.organization_id == org.id)
            )
            if count >= LIMITS[org.plan]["members"]:
                raise ServiceError("Member limit reached for this plan.", 429)
            session.add(Membership(user_id=user_id, organization_id=org.id, role=invitation.role))
        session.delete(invitation)
        audit(session, org.id, "invitation.accepted", user_id)
        return {"organization_id": org.id}


def change_member(membership_id, new_role=None):
    _, org_id = require_identity()
    require_role("admin")
    with session_scope() as session:
        lock_organization(session, org_id)
        member = session.scalar(
            select(Membership).where(
                Membership.id == membership_id, Membership.organization_id == org_id
            )
        )
        if member is None:
            raise ServiceError("Membership not found.", 404)
        if (member.role == "owner" or new_role == "owner") and context.role.get() != "owner":
            raise ServiceError("Only an owner can manage owner access.", 403)
        if member.role == "owner" and new_role != "owner":
            owners = session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.organization_id == org_id, Membership.role == "owner")
            )
            if owners <= 1:
                raise ServiceError("An organization must retain an owner.", 409)
        audit(
            session, org_id, "membership.updated" if new_role else "membership.removed", member.id
        )
        if new_role:
            member.role = new_role
        else:
            session.delete(member)
        return {"status": "updated"}


def audit_log(offset=0):
    _, org = require_identity()
    require_role("admin")
    with session_scope() as session:
        rows = session.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == org)
            .order_by(AuditLog.id.desc())
            .offset(offset)
            .limit(100)
        )
        return [
            {
                "id": row.id,
                "action": row.action,
                "resource_id": row.resource_id,
                "user_id": row.user_id,
                "created_at": row.created_at,
            }
            for row in rows
        ]
