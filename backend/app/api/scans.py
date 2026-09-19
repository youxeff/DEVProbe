from typing import Annotated

from fastapi import APIRouter, Path

from app.schemas.scan import ScanCreatedResponse, ScanRequest, ScanResponse
from app.services import scan_service

router = APIRouter()


@router.post("", response_model=ScanCreatedResponse)
def create_scan(payload: ScanRequest):
    scan = scan_service.create_scan(payload.repo_url, payload.pr_number)
    return {"scan_id": scan.id, "status": scan.status}


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: Annotated[int, Path(gt=0)]):
    return scan_service.get_scan(scan_id)
