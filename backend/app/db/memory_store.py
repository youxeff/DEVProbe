"""Single-process MVP storage. All callers receive independent snapshots."""

from datetime import UTC, datetime
from threading import Lock

from app.core.errors import ServiceError
from app.schemas.scan import ScanResponse


class MemoryScanStore:
    def update_pull_request(self, scan_id: int, metadata: dict) -> None:
        pass  # Test double; repository/PR persistence is exercised using SQLScanStore.

    def __init__(self, max_scans: int = 1000):
        self._scans: dict[int, ScanResponse] = {}
        self._next_id = 1
        self._lock = Lock()
        self.max_scans = max_scans

    def create(self, scan: ScanResponse) -> ScanResponse:
        with self._lock:
            if len(self._scans) >= self.max_scans:
                raise ServiceError("Temporary scan storage is full.", 503)
            scan = scan.model_copy(deep=True, update={"id": self._next_id})
            self._next_id += 1
            self._scans[scan.id] = scan
            return scan.model_copy(deep=True)

    def get(self, scan_id: int) -> ScanResponse | None:
        with self._lock:
            scan = self._scans.get(scan_id)
            return scan.model_copy(deep=True) if scan else None

    def claim(self, scan_id: int) -> tuple[ScanResponse, bool]:
        with self._lock:
            scan = self._scans.get(scan_id)
            if scan is None:
                raise ServiceError("Scan not found.", 404)
            claimed = scan.status == "pending"
            if claimed:
                scan.status = "running"
                scan.started_at = datetime.now(UTC)
            return scan.model_copy(deep=True), claimed

    def save(self, scan: ScanResponse) -> None:
        with self._lock:
            if scan.id not in self._scans:
                raise ServiceError("Scan not found.", 404)
            self._scans[scan.id] = scan.model_copy(deep=True)
