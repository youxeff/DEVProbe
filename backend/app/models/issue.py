from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, utcnow


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column()
    tool: Mapped[str] = mapped_column(String(100))
    rule_id: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
