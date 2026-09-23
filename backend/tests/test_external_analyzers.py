import sys

import pytest

from app.analyzers import bandit_analyzer
from app.analyzers.runner import AnalyzerError, run_json


def test_bandit_real_tool_does_not_execute_source(tmp_path):
    (tmp_path / "sample.py").write_text(
        "raise RuntimeError('must not execute')\npassword = 'never-persist-this-value'\n"
    )
    issues = bandit_analyzer.analyze(tmp_path, ["sample.py"])
    assert any(i.rule_id == "B105" and i.line_number == 2 for i in issues)
    assert "never-persist-this-value" not in str(issues)


def test_runner_timeout_and_secret_free_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "never-inherit-me")
    output = run_json(
        [sys.executable, "-I", "-c", "import os,json; print(json.dumps(dict(os.environ)))"],
        tmp_path,
    )
    assert "GITHUB_TOKEN" not in output
    with pytest.raises(AnalyzerError, match="timed out"):
        run_json([sys.executable, "-I", "-c", "import time; time.sleep(10)"], tmp_path, timeout=0.1)


def test_runner_sanitizes_error(tmp_path):
    with pytest.raises(AnalyzerError) as error:
        run_json(
            [sys.executable, "-I", "-c", "raise RuntimeError('private-source')"],
            tmp_path,
            codes=(0,),
        )
    assert "private-source" not in str(error.value)


def test_radon_real_tool_complexity(tmp_path):
    from app.analyzers import radon_analyzer

    source = "def decide(x):\n" + "".join(f"    if x == {i}: return {i}\n" for i in range(12))
    (tmp_path / "sample.py").write_text(source)
    issues = radon_analyzer.analyze(tmp_path, ["sample.py"])
    assert len(issues) == 1
    assert issues[0].severity == "medium"
    assert issues[0].line_number == 1
    assert "13" in issues[0].message


def test_eslint_real_typescript_ignores_customer_configuration(tmp_path):
    from app.analyzers import eslint_analyzer

    (tmp_path / "sample.ts").write_text("const x: string = 'example';\neval(x);\n")
    (tmp_path / "eslint.config.mjs").write_text(
        "throw new Error('customer config must not execute')"
    )
    issues = eslint_analyzer.analyze(tmp_path, ["sample.ts"])
    assert any(i.rule_id == "no-eval" and i.line_number == 2 for i in issues)


def test_semgrep_real_tool_with_owned_rules(tmp_path):
    from app.analyzers import semgrep_analyzer

    (tmp_path / "sample.py").write_text("eval(input())\n")
    issues = semgrep_analyzer.analyze(tmp_path, ["sample.py"])
    assert any(i.rule_id == "devprobe-python-eval" and i.line_number == 1 for i in issues)


def test_pipeline_preserves_findings_on_tool_failure(monkeypatch):
    from app.core.config import Settings
    from app.schemas.issue import IssueResponse
    from app.schemas.pull_request import ChangedFileResponse
    from app.services import github_service
    from app.services import static_analysis_service as service

    monkeypatch.setattr(
        service, "get_settings", lambda: Settings(external_analyzers="bandit,radon")
    )
    calls = []

    def source(repo, filename, sha):
        calls.append((filename, sha))
        return "password = 'fixture'\n"

    monkeypatch.setattr(github_service, "fetch_file_at_commit", source)
    monkeypatch.setattr(
        service.ANALYZERS["bandit"],
        "analyze",
        lambda path, names: [
            IssueResponse(
                file_path=names[0],
                line_number=1,
                tool="bandit",
                category="security",
                severity="high",
                message="Safe finding",
                recommendation="Review",
            )
        ],
    )

    def fail(*args):
        raise RuntimeError("never-persist-source")

    monkeypatch.setattr(service.ANALYZERS["radon"], "analyze", fail)
    files = [
        ChangedFileResponse(
            filename="src/a.py",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch="@@ -0,0 +1 @@\n+password = 'fixture'",
        )
    ]
    issues, warnings, runs = service.analyze("https://github.com/o/r", "a" * 40, files)
    assert calls == [("src/a.py", "a" * 40)]
    assert issues[0].file_path == "src/a.py"
    assert runs[1]["status"] == "failed"
    assert "never-persist-source" not in str(warnings)
