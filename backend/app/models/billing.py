from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, utcnow


class Subscription(Base):
    __tablename__ = "subscriptions"
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="none")
    checkout_session_id: Mapped[str | None] = mapped_column(String(100))
    checkout_url: Mapped[str | None] = mapped_column(String(2000))
    checkout_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingEvent(Base):
    __tablename__ = "billing_events"
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
