from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.core.security import require_identity
from app.schemas.organization import (
    AcceptInvitation,
    InviteRequest,
    OrganizationRequest,
    RoleRequest,
)
from app.services import organization_service, usage_service

router = APIRouter()


@router.post("", status_code=201)
def create(payload: OrganizationRequest):
    return organization_service.create(payload.name)


@router.get("/members")
def members():
    return organization_service.members()


@router.post("/invitations", status_code=201)
def invite(payload: InviteRequest):
    return organization_service.invite(str(payload.email), payload.role)


@router.post("/invitations/accept")
def accept(payload: AcceptInvitation):
    return organization_service.accept(payload.token)


@router.patch("/members/{membership_id}")
def change_member(membership_id: Annotated[int, Path(gt=0)], payload: RoleRequest):
    return organization_service.change_member(membership_id, payload.role)


@router.delete("/members/{membership_id}")
def remove_member(membership_id: Annotated[int, Path(gt=0)]):
    return organization_service.change_member(membership_id)


@router.get("/usage")
def usage():
    _, org = require_identity()
    return usage_service.usage(org)


@router.get("/audit")
def audit(offset: Annotated[int, Query(ge=0)] = 0):
    return organization_service.audit_log(offset)
