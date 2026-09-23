from app.core.errors import ScanExecutionError
from app.services import scan_service
from app.workers.celery_app import celery_app


@celery_app.task(name="devprobe.scan")
def run_scan(scan_id: int):
    try:
        result = scan_service.execute_scan(scan_id)
        return {"scan_id": result.id, "status": result.status}
    except ScanExecutionError:
        return {"scan_id": scan_id, "status": "failed"}


@celery_app.task(name="devprobe.recover_scans")
def recover_scans():
    from app.services.job_service import recover

    return recover()
