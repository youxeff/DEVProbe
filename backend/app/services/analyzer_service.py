"""Coordinate analyzers and validate/deduplicate their canonical output."""

from app.analyzers import basic_analyzer
from app.schemas.issue import IssueResponse
from app.schemas.pull_request import ChangedFileResponse


def normalize_issues(findings: list[IssueResponse | dict]) -> list[IssueResponse]:
    normalized = []
    seen = set()
    for finding in findings:
        issue = IssueResponse.model_validate(finding)
        fingerprint = (
            issue.tool,
            issue.rule_id,
            issue.file_path,
            issue.line_number,
            issue.category,
            issue.severity,
            issue.message,
        )
        if fingerprint not in seen:
            seen.add(fingerprint)
            normalized.append(issue)
    return normalized


def analyze_changed_files(files: list[ChangedFileResponse | dict]) -> list[IssueResponse]:
    changed_files = [ChangedFileResponse.model_validate(file) for file in files]
    return normalize_issues(basic_analyzer.analyze(changed_files))
