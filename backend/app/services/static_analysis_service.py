"""Optional tools operate on bounded, temporary copies of changed source files."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from app.analyzers import bandit_analyzer, eslint_analyzer, radon_analyzer, semgrep_analyzer
from app.analyzers.basic_analyzer import CODE_SUFFIXES, added_lines
from app.core.config import get_settings
from app.core.errors import ServiceError
from app.schemas.pull_request import ChangedFileResponse
from app.services import github_service
from app.services.analyzer_service import normalize_issues

ANALYZERS = {
    "bandit": bandit_analyzer,
    "radon": radon_analyzer,
    "eslint": eslint_analyzer,
    "semgrep": semgrep_analyzer,
}
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", "generated", ".git"}


def analyze(repo_url: str, head_sha: str, files: list[ChangedFileResponse]):
    settings = get_settings()
    enabled = [name.strip() for name in settings.external_analyzers.split(",") if name.strip()]
    issues, warnings, executions = [], [], []
    if not enabled:
        return issues, warnings, executions
    with TemporaryDirectory(prefix="devprobe-") as directory:
        workspace = Path(directory)
        sources, lines = {}, {}
        total_bytes = 0
        for file in files:
            path = Path(file.filename)
            if (
                file.status == "removed"
                or path.suffix not in CODE_SUFFIXES
                or set(path.parts) & SKIP_PARTS
                or ".min." in path.name
                or not file.patch
            ):
                continue
            if len(sources) >= settings.analyzer_max_files:
                warnings.append("Static source file limit reached; remaining files were skipped.")
                break
            try:
                source = github_service.fetch_file_at_commit(repo_url, file.filename, head_sha)
                total_bytes += len(source.encode())
                if total_bytes > 5_000_000:
                    warnings.append(
                        "Static source size limit reached; remaining files were skipped."
                    )
                    break
                name = f"file_{len(sources)}{path.suffix}"
                (workspace / name).write_text(source, encoding="utf-8")
                sources[name] = file.filename
                lines[name] = {number for number, _ in added_lines(file.patch)}
            except ServiceError:
                warnings.append(f"Source retrieval skipped for {file.filename}.")
        for name in enabled:
            started = perf_counter()
            status = "completed"
            try:
                tool = ANALYZERS[name]
                findings = tool.analyze(workspace, list(sources))
                for issue in findings:
                    original = sources.get(issue.file_path)
                    if not original:
                        continue
                    # Complexity is a whole-function metric; include changed-file functions.
                    if name == "radon" or issue.line_number in lines[issue.file_path]:
                        issue.file_path = original
                        issues.append(issue)
            except Exception:
                status = "failed"
                warnings.append(
                    f"{name}: analysis unavailable or incomplete; other results retained."
                )
            executions.append(
                {
                    "tool": name,
                    "status": status,
                    "duration_seconds": round(perf_counter() - started, 6),
                    "files_supplied": len(sources),
                }
            )
    return normalize_issues(issues), warnings, executions
