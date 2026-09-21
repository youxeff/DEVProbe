from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import JSON_TYPE, Base, utcnow


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    risks: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    suggested_tests: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    recommended_fixes: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    model_name: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
