from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.scan import ScanResponse


class ScanPage(BaseModel):
    items: list[ScanResponse]
    total: int
    offset: int
    limit: int


class TrendPoint(BaseModel):
    scan_id: int
    created_at: datetime
    risk_score: int
    total_issues: int


class AnalyticsResponse(BaseModel):
    total_scans: int = 0
    completed_scans: int = 0
    failed_scans: int = 0
    prs_analyzed: int = 0
    files_analyzed: int = 0
    changed_lines_analyzed: int = 0
    total_issues: int = 0
    average_risk_score: float | None = None
    average_duration_seconds: float | None = None
    failure_rate: float = 0
    ai_reviews: int = 0
    ai_input_tokens: int = 0
    ai_output_tokens: int = 0
    ai_estimated_cost: float | None = None
    severity_counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    trend: list[TrendPoint] = Field(default_factory=list)
