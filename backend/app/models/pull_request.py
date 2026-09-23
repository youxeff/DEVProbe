from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, Timestamps


class PullRequest(Base, Timestamps):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "github_pr_number", name="uq_repo_pr"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    github_pr_number: Mapped[int] = mapped_column()
    title: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(30))
    author: Mapped[str | None] = mapped_column(String(100))
    base_branch: Mapped[str | None] = mapped_column(String(300))
    head_branch: Mapped[str | None] = mapped_column(String(300))
    html_url: Mapped[str | None] = mapped_column(String(600))
    github_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    github_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
