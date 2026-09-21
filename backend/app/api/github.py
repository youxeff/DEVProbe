from typing import Annotated

from fastapi import APIRouter, Path, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services import integration_service

router = APIRouter()


class ConnectionRequest(BaseModel):
    installation_id: int = Field(gt=0)


class InstallationSettings(BaseModel):
    publish_checks: bool


@router.get("")
def settings():
    return integration_service.settings_view()


@router.post("/connect")
def connect(payload: ConnectionRequest):
    return integration_service.start_connection(payload.installation_id)


@router.get("/callback")
def callback(
    code: Annotated[str, Query(min_length=1, max_length=500)],
    state: Annotated[str, Query(min_length=20, max_length=200)],
):
    integration_service.finish_connection(code, state)
    return RedirectResponse(
        get_settings().public_url + "/settings?github=connected", status_code=303
    )


@router.patch("/installations/{installation_id}")
def update(installation_id: Annotated[int, Path(gt=0)], payload: InstallationSettings):
    return integration_service.update_installation(
        installation_id, publish_checks=payload.publish_checks
    )


@router.delete("/installations/{installation_id}")
def disconnect(installation_id: Annotated[int, Path(gt=0)]):
    return integration_service.update_installation(installation_id, disconnect=True)


@router.post("/scans/{scan_id}/check")
def publish(scan_id: Annotated[int, Path(gt=0)]):
    return integration_service.publish_for_user(scan_id)
