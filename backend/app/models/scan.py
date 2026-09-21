from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import JSON_TYPE, Base, utcnow


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="ck_scan_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, index=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    pull_request_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True
    )
    repo_url: Mapped[str] = mapped_column(String(500))
    pr_number: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    trigger_source: Mapped[str] = mapped_column(String(20), default="manual")
    head_sha: Mapped[str | None] = mapped_column(String(64))
    base_sha: Mapped[str | None] = mapped_column(String(64))
    scoring_version: Mapped[str] = mapped_column(String(20), default="1")
    risk_score: Mapped[int | None] = mapped_column()
    risk_level: Mapped[str | None] = mapped_column(String(20))
    changed_files_count: Mapped[int] = mapped_column(default=0)
    additions: Mapped[int] = mapped_column(default=0)
    deletions: Mapped[int] = mapped_column(default=0)
    total_changed_lines: Mapped[int] = mapped_column(default=0)
    total_issues: Mapped[int] = mapped_column(default=0)
    security_count: Mapped[int] = mapped_column(default=0)
    complexity_count: Mapped[int] = mapped_column(default=0)
    style_count: Mapped[int] = mapped_column(default=0)
    testing_count: Mapped[int] = mapped_column(default=0)
    maintainability_count: Mapped[int] = mapped_column(default=0)
    documentation_count: Mapped[int] = mapped_column(default=0)
    files_with_patch: Mapped[int] = mapped_column(default=0)
    files_without_patch: Mapped[int] = mapped_column(default=0)
    scan_duration_seconds: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    ai_status: Mapped[str] = mapped_column(String(20), default="disabled")
    ai_model: Mapped[str | None] = mapped_column(String(100))
    ai_input_tokens: Mapped[int] = mapped_column(default=0)
    ai_output_tokens: Mapped[int] = mapped_column(default=0)
    ai_estimated_cost: Mapped[float | None] = mapped_column()
    tool_executions: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    analysis_warnings: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    issues: Mapped[list["Issue"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan", passive_deletes=True, order_by="Issue.id"
    )
    ai_review: Mapped["AIReview | None"] = relationship(  # noqa: F821
        cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
