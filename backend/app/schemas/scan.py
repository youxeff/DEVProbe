from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.issue import IssueResponse
from app.schemas.repository import RepoUrlRequest

ScanStatus = Literal["pending", "running", "completed", "failed"]
TriggerSource = Literal["manual", "webhook", "scheduled"]


class ScanRequest(RepoUrlRequest):
    pr_number: int = Field(gt=0, strict=True)


class ScanCreatedResponse(BaseModel):
    scan_id: int
    status: ScanStatus


class ScanResponse(BaseModel):
    id: int = 0
    organization_id: int | None = None
    repository_id: int | None = None
    pull_request_id: int | None = None
    repo_url: str
    pr_number: int
    status: ScanStatus = "pending"
    trigger_source: TriggerSource = "manual"
    head_sha: str | None = None
    base_sha: str | None = None
    scoring_version: str = "1"
    risk_score: int | None = None
    risk_level: Literal["Low", "Medium", "High", "Critical"] | None = None
    changed_files_count: int = 0
    additions: int = 0
    deletions: int = 0
    total_changed_lines: int = 0
    total_issues: int = 0
    security_count: int = 0
    complexity_count: int = 0
    style_count: int = 0
    testing_count: int = 0
    maintainability_count: int = 0
    documentation_count: int = 0
    files_with_patch: int = 0
    files_without_patch: int = 0
    scan_duration_seconds: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_reason: str | None = None
    issues: list[IssueResponse] = Field(default_factory=list)
    analysis_warnings: list[str] = Field(default_factory=list)
