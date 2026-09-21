from fastapi import APIRouter, HTTPException

from app.schemas.scan import ScanRequest
from app.services.scan_service import create_scan_result
from app.db.memory_store import save_scan, get_scan_by_id


router = APIRouter()


@router.post("")
def create_scan(payload: ScanRequest):
    scan_result = create_scan_result(payload.repo_url, payload.pr_number)
    scan_id = save_scan(scan_result)

    return {
        "scan_id": scan_id,
        "status": scan_result["status"]
    }


@router.get("/{scan_id}")
def get_scan(scan_id: int):
    scan = get_scan_by_id(scan_id)

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    return scan