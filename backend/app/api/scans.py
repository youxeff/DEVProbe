from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.schemas.analytics import ScanPage
from app.schemas.scan import ScanCreatedResponse, ScanRequest, ScanResponse
from app.services import analytics_service, scan_service

router = APIRouter()


@router.post("", response_model=ScanCreatedResponse)
def create_scan(payload: ScanRequest):
    scan = scan_service.create_scan(payload.repo_url, payload.pr_number)
    return {"scan_id": scan.id, "status": scan.status}


@router.get("", response_model=ScanPage)
def list_scans(
    repository_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    return analytics_service.history(repository_id=repository_id, offset=offset, limit=limit)


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: Annotated[int, Path(gt=0)]):
    return scan_service.get_scan(scan_id)
