from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "member", "viewer"]


class OrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


class AcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200, repr=False)


class RoleRequest(BaseModel):
    role: Role
