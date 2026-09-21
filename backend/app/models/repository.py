from sqlalchemy import BigInteger, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import JSON_TYPE, Base, Timestamps


class Repository(Base, Timestamps):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("scope_key", "full_name", name="uq_repo_scope_name"),
        UniqueConstraint("scope_key", "github_repo_id", name="uq_repo_scope_github"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, index=True)
    scope_key: Mapped[int] = mapped_column(default=0)  # 0 = local development; org id later.
    github_repo_id: Mapped[int | None] = mapped_column(BigInteger)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(320))
    html_url: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    default_branch: Mapped[str | None] = mapped_column(String(300))
    language: Mapped[str | None] = mapped_column(String(100))
    stars: Mapped[int] = mapped_column(default=0)
    forks: Mapped[int] = mapped_column(default=0)
    open_issues: Mapped[int] = mapped_column(default=0)
    contributors: Mapped[list] = mapped_column(JSON_TYPE, default=list)
