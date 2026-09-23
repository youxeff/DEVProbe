from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.security import require_user
from app.schemas.user import LoginRequest, PasswordChange, RegisterRequest
from app.services import auth_service

router = APIRouter()


def cookies(response: Response, token: str, csrf: str):
    settings = get_settings()
    for name, value in (("dp_session", token), ("dp_csrf", csrf)):
        response.set_cookie(
            name,
            value,
            httponly=name == "dp_session",
            secure=settings.public_url.startswith("https://"),
            samesite="lax",
            max_age=settings.session_ttl_seconds,
            path="/",
        )


@router.get("/session")
def session(request: Request):
    identity = request.state.identity
    return {
        "enabled": get_settings().auth_enabled,
        "registration_enabled": get_settings().registration_enabled,
        **(
            {key: value for key, value in identity.items() if key != "csrf_hash"}
            if identity
            else {"user": None, "organizations": [], "active_organization": None}
        ),
    }


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, request: Request, response: Response):
    token, csrf = auth_service.register(
        payload, request.client.host if request.client else "unknown"
    )
    auth_service.logout(request.cookies.get("dp_session"))
    cookies(response, token, csrf)
    return {"status": "signed_in"}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    token, csrf = auth_service.login(payload, request.client.host if request.client else "unknown")
    auth_service.logout(request.cookies.get("dp_session"))
    cookies(response, token, csrf)
    return {"status": "signed_in"}


@router.post("/logout")
def logout(request: Request, response: Response):
    auth_service.logout(request.cookies.get("dp_session"))
    response.delete_cookie("dp_session", path="/")
    response.delete_cookie("dp_csrf", path="/")
    return {"status": "signed_out"}


@router.post("/password")
def password(payload: PasswordChange, response: Response):
    user = require_user()
    auth_service.change_password(user, payload)
    response.delete_cookie("dp_session", path="/")
    response.delete_cookie("dp_csrf", path="/")
    return {"status": "signed_out"}
