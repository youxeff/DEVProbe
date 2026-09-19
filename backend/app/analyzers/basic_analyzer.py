"""Heuristics only. Never execute code or include matched source in a finding."""

import re
from pathlib import PurePosixPath

from app.schemas.issue import IssueResponse
from app.schemas.pull_request import ChangedFileResponse

TOOL = "devprobe-basic"
CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"}
SECRET_WORDS = ("password", "secret", "api_key", "apikey", "token", "private_key", "access_key")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# A quoted literal on the RHS is stronger evidence than a keyword alone.
LITERAL = re.compile(
    r"\b[\w]*?(?:password|secret|api_key|apikey|token|private_key|access_key)[\w]*"
    r"[\"']?\s*(?::\s*str\s*)?[:=]\s*[\"']([^\"'\r\n]+)[\"']",
    re.IGNORECASE,
)


def is_test_file(filename: str) -> bool:
    parts = PurePosixPath(filename.lower()).parts
    name = parts[-1] if parts else ""
    return (
        any(part in {"tests", "test", "__tests__"} for part in parts[:-1])
        or name.startswith("test_")
        or "_test." in name
        or ".test." in name
        or ".spec." in name
    )


def added_lines(patch: str):
    """Yield new-file coordinates; ignore removed lines and unchanged context."""
    line_number = None
    for line in patch.splitlines():
        hunk = HUNK.match(line)
        if hunk:
            line_number = int(hunk.group(1))
        elif line_number is not None:
            if line.startswith("+"):
                yield line_number, line[1:]
                line_number += 1
            elif line.startswith(" "):
                line_number += 1
            elif not line.startswith(("-", "\\")):
                line_number = None


def _issue(path, line, rule, category, severity, message, recommendation) -> IssueResponse:
    return IssueResponse(
        file_path=path,
        line_number=line,
        tool=TOOL,
        rule_id=rule,
        category=category,
        severity=severity,
        message=message,
        recommendation=recommendation,
    )


def analyze(files: list[ChangedFileResponse]) -> list[IssueResponse]:
    issues = []
    total_changes = sum(file.additions + file.deletions for file in files)
    if len(files) > 15:
        issues.append(
            _issue(
                "PR-level",
                None,
                "large-pr-files",
                "maintainability",
                "medium",
                "Large pull request detected.",
                "Consider splitting this PR into smaller, easier-to-review changes.",
            )
        )
    if total_changes > 500:
        issues.append(
            _issue(
                "PR-level",
                None,
                "large-pr-lines",
                "maintainability",
                "medium",
                "Large number of changed lines detected.",
                "Consider breaking this work into smaller PRs.",
            )
        )

    # Deleted tests do not demonstrate coverage for newly changed behavior.
    has_tests = any(
        is_test_file(f.filename) and f.status != "removed" and f.additions > 0 for f in files
    )
    has_code = any(
        PurePosixPath(f.filename.lower()).suffix in CODE_SUFFIXES
        and not is_test_file(f.filename)
        and f.additions + f.deletions > 0
        for f in files
    )
    if has_code and not has_tests:
        issues.append(
            _issue(
                "PR-level",
                None,
                "missing-tests",
                "testing",
                "medium",
                "Code changed without added or updated test lines (heuristic).",
                "Add or update tests for the changed behavior; existing tests may apply.",
            )
        )

    for file in files:
        if file.additions + file.deletions > 250:
            issues.append(
                _issue(
                    file.filename,
                    None,
                    "large-file-change",
                    "maintainability",
                    "medium",
                    "Large file change detected.",
                    "Review this file carefully or split it into smaller changes.",
                )
            )
        for line_number, line in added_lines(file.patch or ""):
            keywords = any(word in line.lower() for word in SECRET_WORDS)
            if keywords:
                literal = LITERAL.search(line)
                suspicious = bool(literal and literal.group(1).strip())
                issues.append(
                    _issue(
                        file.filename,
                        line_number,
                        "possible-hardcoded-secret" if suspicious else "sensitive-keyword",
                        "security",
                        "high" if suspicious else "info",
                        "Possible hardcoded sensitive value (heuristic; verify manually)."
                        if suspicious
                        else "Sensitive keyword in added code; not a confirmed vulnerability.",
                        "Verify the value; use environment variables or a secrets manager.",
                    )
                )
            for pattern, rule, message, recommendation in [
                (
                    r"\bconsole\s*\.\s*log\s*\(",
                    "console-log",
                    "console.log found in added code.",
                    "Remove debug logging before merging if it is not intentional.",
                ),
                (
                    r"\bprint\s*\(",
                    "debug-print",
                    "print() found in added code.",
                    "Remove debug prints or replace them with structured logging if appropriate.",
                ),
                (
                    r"\bTODO\b",
                    "todo",
                    "TODO found in added code.",
                    "Resolve the TODO or create a tracking issue.",
                ),
                (
                    r"\bFIXME\b",
                    "fixme",
                    "FIXME found in added code.",
                    "Resolve the FIXME or create a tracking issue.",
                ),
            ]:
                if re.search(pattern, line):
                    category = (
                        "style" if rule in ("console-log", "debug-print") else "maintainability"
                    )
                    issues.append(
                        _issue(
                            file.filename,
                            line_number,
                            rule,
                            category,
                            "low",
                            message,
                            recommendation,
                        )
                    )
    return issues
