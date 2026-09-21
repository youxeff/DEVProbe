import sys
from pathlib import Path

from app.analyzers.runner import AnalyzerError, run_json
from app.schemas.issue import IssueResponse


def analyze(workspace: Path, names: list[str]) -> list[IssueResponse]:
    names = [name for name in names if name.endswith(".py")]
    if not names:
        return []
    data = run_json(
        [sys.executable, "-I", "-m", "radon", "cc", "-j", *names], workspace, codes=(0,)
    )
    issues = []
    for path, blocks in data.items():
        if isinstance(blocks, dict):
            raise AnalyzerError("some Python files could not be parsed")
        for block in blocks:
            # Radon class scores are aggregates; report individual functions/methods once.
            candidates = block.get("methods", []) if block["type"] == "class" else [block]
            for item in candidates:
                if item["complexity"] <= 10:
                    continue
                issues.append(
                    IssueResponse(
                        file_path=Path(path).name,
                        line_number=item["lineno"],
                        tool="radon",
                        rule_id="cyclomatic-complexity",
                        category="complexity",
                        severity="high" if item["complexity"] > 20 else "medium",
                        message=f"Cyclomatic complexity is {item['complexity']}.",
                        recommendation="Split functions and test each conditional branch.",
                    )
                )
    return issues
