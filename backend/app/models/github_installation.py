from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, Timestamps, utcnow


class GitHubInstallation(Base, Timestamps):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, index=True)
    github_installation_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    account_login: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(default=True)
    publish_checks: Mapped[bool] = mapped_column(default=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    delivery_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    dedup_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    event: Mapped[str] = mapped_column(String(100))
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GitHubCheck(Base):
    __tablename__ = "github_checks"
    __table_args__ = (UniqueConstraint("repository_id", "head_sha", name="uq_check_repo_sha"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    head_sha: Mapped[str] = mapped_column(String(64))
    check_run_id: Mapped[int | None] = mapped_column(BigInteger)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"))
