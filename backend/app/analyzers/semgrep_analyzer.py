from pathlib import Path

from app.analyzers.runner import AnalyzerError, run_json
from app.schemas.issue import IssueResponse

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def analyze(workspace: Path, names: list[str]) -> list[IssueResponse]:
    if not names:
        return []
    executable = TOOLS / ".venv/bin/semgrep"
    data = run_json(
        [
            str(executable),
            "scan",
            "--config",
            str(TOOLS / "semgrep-rules.yml"),
            "--json",
            "--metrics=off",
            "--disable-version-check",
            "--no-git-ignore",
            "--no-rewrite-rule-ids",
            "--oss-only",
            "--jobs=1",
            "--timeout=10",
            "--max-memory=512",
            "--disable-nosem",
            *names,
        ],
        workspace,
        timeout=45,
        codes=(0,),
    )
    if data.get("errors"):
        raise AnalyzerError("some files could not be parsed")
    return [
        IssueResponse(
            file_path=Path(row["path"]).name,
            line_number=row["start"]["line"],
            tool="semgrep",
            rule_id=row["check_id"],
            category="security",
            severity="high",
            message="Potential unsafe evaluation or shell invocation detected.",
            recommendation="Avoid executing untrusted input; validate inputs and use safer APIs.",
        )
        for row in data["results"]
    ]
