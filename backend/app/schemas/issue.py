from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["security", "complexity", "style", "testing", "maintainability", "documentation"]
Severity = Literal["critical", "high", "medium", "low", "info"]


class IssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    line_number: int | None = Field(default=None, ge=1)
    tool: str
    category: Category
    severity: Severity
    message: str
    recommendation: str
    rule_id: str | None = None
