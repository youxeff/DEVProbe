import sys
from pathlib import Path

from app.analyzers.runner import AnalyzerError, run_json
from app.schemas.issue import IssueResponse

# Owned explanations prevent raw tool messages from copying literals into persistence.
EXPLANATIONS = {
    "B105": "Possible hardcoded password detected by Bandit; verify manually.",
    "B106": "Possible hardcoded password argument detected by Bandit; verify manually.",
    "B307": "Dynamic evaluation detected; avoid evaluating untrusted input.",
    "B602": "Shell invocation detected; review command construction and input validation.",
    "B608": "Possible SQL query construction risk; use parameterized statements.",
}


def analyze(workspace: Path, names: list[str]) -> list[IssueResponse]:
    names = [name for name in names if name.endswith(".py")]
    if not names:
        return []
    data = run_json(
        [sys.executable, "-I", "-m", "bandit", "-q", "-f", "json", "--ignore-nosec", *names],
        workspace,
    )
    if data.get("errors"):
        raise AnalyzerError("some Python files could not be parsed")
    return [
        IssueResponse(
            file_path=Path(row["filename"]).name,
            line_number=row["line_number"],
            tool="bandit",
            category="security",
            severity=row["issue_severity"].lower(),
            rule_id=row["test_id"],
            message=EXPLANATIONS.get(
                row["test_id"], f"Bandit security rule {row['test_id']} requires review."
            ),
            recommendation="Review this location and the Bandit rule guidance.",
        )
        for row in data["results"]
    ]
