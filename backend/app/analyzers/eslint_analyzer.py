import shutil
from pathlib import Path

from app.analyzers.runner import AnalyzerError, run_json
from app.schemas.issue import IssueResponse

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def analyze(workspace: Path, names: list[str]) -> list[IssueResponse]:
    names = [
        name
        for name in names
        if Path(name).suffix in {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"}
    ]
    if not names:
        return []
    node = shutil.which("node")
    if not node:
        raise AnalyzerError("Node.js unavailable")
    data = run_json(
        [
            node,
            str(TOOLS / "node_modules/eslint/bin/eslint.js"),
            "--no-config-lookup",
            "--no-inline-config",
            "--no-ignore",
            "--config",
            str(TOOLS / "eslint.config.mjs"),
            "--format",
            "json",
            *names,
        ],
        workspace,
    )
    issues = []
    for file in data:
        for item in file["messages"]:
            if item.get("fatal") or not item.get("ruleId"):
                raise AnalyzerError("some JavaScript/TypeScript files could not be parsed")
            security = item["ruleId"] in {"no-eval", "no-implied-eval"}
            issues.append(
                IssueResponse(
                    file_path=Path(file["filePath"]).name,
                    line_number=item["line"],
                    tool="eslint",
                    rule_id=item["ruleId"],
                    category="security" if security else "style",
                    severity="high" if security else "low",
                    message=f"ESLint rule {item['ruleId']} requires review.",
                    recommendation="Review this location and follow the ESLint rule guidance.",
                )
            )
    return issues
