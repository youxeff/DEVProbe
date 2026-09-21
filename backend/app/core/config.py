"""Only this module reads application environment configuration."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_env: str = "development"
    database_url: str = Field(default="sqlite:///./devprobe.db", repr=False)
    github_token: SecretStr | None = None
    github_timeout_seconds: float = Field(default=10, gt=0, le=60)
    github_max_pages: int = Field(default=30, ge=1, le=100)
    github_max_response_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)


@lru_cache
def get_settings() -> Settings:
    # Resolve consistently whether launched from the root or backend directory.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./devprobe.db"),
        github_token=os.getenv("GITHUB_TOKEN") or None,
        github_timeout_seconds=os.getenv("GITHUB_TIMEOUT_SECONDS", "10"),
        github_max_pages=os.getenv("GITHUB_MAX_PAGES", "30"),
        github_max_response_bytes=os.getenv("GITHUB_MAX_RESPONSE_BYTES", "8388608"),
    )
