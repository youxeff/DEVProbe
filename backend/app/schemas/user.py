from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128, repr=False)


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=100)
    organization_name: str = Field(min_length=1, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=12, max_length=128, repr=False)
    new_password: str = Field(min_length=12, max_length=128, repr=False)
