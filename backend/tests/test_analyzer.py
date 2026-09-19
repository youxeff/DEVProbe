import pytest
from pydantic import ValidationError

from app.analyzers.basic_analyzer import added_lines, is_test_file
from app.services.analyzer_service import analyze_changed_files, normalize_issues


def file(name="app.py", patch=None, additions=1, deletions=0, status="modified"):
    return {
        "filename": name,
        "patch": patch,
        "additions": additions,
        "deletions": deletions,
        "changes": additions + deletions,
        "status": status,
    }


@pytest.mark.parametrize(
    "name",
    [
        "test_app.py",
        "auth_test.py",
        "auth.test.ts",
        "auth.spec.tsx",
        "__tests__/auth.ts",
        "backend/tests/auth.py",
        "test/Auth.ts",
        "tests/unit/test_auth.py",
    ],
)
def test_test_detection(name):
    assert is_test_file(name)


@pytest.mark.parametrize(
    "name", ["contest.py", "latest_changes.ts", "docs/testing.md", "src/app.py"]
)
def test_non_test_detection(name):
    assert not is_test_file(name)


def test_diff_locations_across_hunks():
    patch = '@@ -2,3 +2,3 @@\n keep\n-print("removed")\n+print("added")\n keep\n'
    patch += "@@ -10 +20,2 @@\n-old\n+# TODO\n+new\n\\ No newline at end of file"
    assert list(added_lines(patch)) == [(3, 'print("added")'), (20, "# TODO"), (21, "new")]


def test_ignores_deleted_context_and_patchless_files():
    issues = analyze_changed_files(
        [
            file(patch='@@ -1,2 +1 @@\n-print("removed secret")\n # TODO unchanged'),
            file("image.png"),
        ]
    )
    assert [issue.rule_id for issue in issues] == ["missing-tests"]


def test_all_requested_line_rules_and_no_secret_leak():
    secret = "private-demo-value-not-a-real-key"
    patch = (
        f'@@ -0,0 +1,5 @@\n+password = "{secret}"\n+console.log(x)\n+print(x)\n+# TODO\n+# FIXME'
    )
    issues = analyze_changed_files([file(patch=patch, additions=5)])
    assert {i.rule_id for i in issues} == {
        "missing-tests",
        "possible-hardcoded-secret",
        "console-log",
        "debug-print",
        "todo",
        "fixme",
    }
    assert {i.line_number for i in issues if i.line_number} == {1, 2, 3, 4, 5}
    assert secret not in str([i.model_dump() for i in issues])
    assert "heuristic" in next(i.message for i in issues if i.category == "security")


@pytest.mark.parametrize(
    "keyword",
    [
        "password",
        "secret",
        "api_key",
        "apikey",
        "token",
        "private_key",
        "access_key",
    ],
)
def test_sensitive_keywords_are_heuristics(keyword):
    issues = analyze_changed_files([file(patch=f'@@ -0,0 +1 @@\n+{keyword} = os.getenv("VALUE")')])
    security = [i for i in issues if i.category == "security"]
    assert len(security) == 1
    assert security[0].severity == "info"


def test_test_only_changes_and_docs_dont_need_tests():
    assert not analyze_changed_files([file("tests/auth.py"), file("README.md")])


def test_added_tests_suppress_warning():
    assert not analyze_changed_files([file(), file("auth.spec.ts")])


def test_deleted_tests_do_not_suppress_warning():
    issues = analyze_changed_files(
        [file(), file("test_app.py", additions=0, deletions=5, status="removed")]
    )
    assert any(i.rule_id == "missing-tests" for i in issues)


def test_large_change_thresholds():
    issues = analyze_changed_files([file(f"doc{i}.md", additions=251) for i in range(16)])
    rules = [i.rule_id for i in issues]
    assert rules.count("large-pr-files") == 1
    assert rules.count("large-pr-lines") == 1
    assert rules.count("large-file-change") == 16
    assert not analyze_changed_files([file("a.md", additions=250), file("b.md", additions=250)])


def test_normalize_validates_and_deduplicates():
    issue = analyze_changed_files([file()])[0]
    assert normalize_issues([issue, issue.model_dump()]) == [issue]
    with pytest.raises(ValidationError):
        normalize_issues([{**issue.model_dump(), "severity": "dangerous"}])
    with pytest.raises(ValidationError):
        normalize_issues([{**issue.model_dump(), "raw_source": "must not persist"}])


def test_patch_headers_are_not_added_lines():
    assert list(added_lines("--- a/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+++counter")) == [
        (1, "++counter")
    ]
