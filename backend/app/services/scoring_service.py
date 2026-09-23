"""Version 1: uncapped, deterministic scoring; no IO and no prose matching."""

from typing import Literal

from app.schemas.issue import IssueResponse

RiskLevel = Literal["Low", "Medium", "High", "Critical"]
SECURITY_POINTS = {"critical": 15, "high": 10, "medium": 6, "low": 3, "info": 0}
COMPLEXITY_POINTS = {"high": 5, "medium": 3}


def classify_risk(score: int) -> RiskLevel:
    if score < 0:
        raise ValueError("Risk score cannot be negative.")
    if score <= 20:
        return "Low"
    if score <= 50:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def calculate_risk(
    issues: list[IssueResponse], changed_files_count: int, total_changed_lines: int
) -> tuple[int, RiskLevel]:
    if changed_files_count < 0 or total_changed_lines < 0:
        raise ValueError("Change metrics cannot be negative.")
    score = 0
    for issue in issues:
        if issue.category == "security":
            score += SECURITY_POINTS[issue.severity]
        elif issue.category == "complexity":
            score += COMPLEXITY_POINTS.get(issue.severity, 0)
        elif issue.category == "style" and issue.severity != "info":
            score += 2
        elif issue.rule_id == "missing-tests":
            score += 4
        elif issue.rule_id == "large-file-change":
            score += 2
    # PR-level size findings are informational here; apply these penalties only once.
    if changed_files_count > 15:
        score += 10
    if total_changed_lines > 1000:
        score += 20
    elif total_changed_lines > 500:
        score += 10
    return score, classify_risk(score)
