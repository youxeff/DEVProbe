import pytest

from app.schemas.issue import IssueResponse
from app.services.scoring_service import calculate_risk, classify_risk


def issue(category, severity, rule_id=None):
    return IssueResponse(
        file_path="app.py",
        tool="test",
        category=category,
        severity=severity,
        rule_id=rule_id,
        message="finding",
        recommendation="review",
    )


@pytest.mark.parametrize(
    "score,level",
    [
        (0, "Low"),
        (20, "Low"),
        (21, "Medium"),
        (50, "Medium"),
        (51, "High"),
        (80, "High"),
        (81, "Critical"),
        (150, "Critical"),
    ],
)
def test_risk_boundaries(score, level):
    assert classify_risk(score) == level


@pytest.mark.parametrize(
    "category,severity,rule,points",
    [
        ("security", "critical", None, 15),
        ("security", "high", None, 10),
        ("security", "medium", None, 6),
        ("security", "low", None, 3),
        ("security", "info", None, 0),
        ("complexity", "high", None, 5),
        ("complexity", "medium", None, 3),
        ("style", "low", None, 2),
        ("style", "info", None, 0),
        ("testing", "medium", "missing-tests", 4),
        ("maintainability", "medium", "large-file-change", 2),
        ("maintainability", "medium", "large-pr-lines", 0),
        ("maintainability", "medium", "large-pr-files", 0),
        ("maintainability", "low", "todo", 0),
        ("documentation", "info", None, 0),
    ],
)
def test_each_weight(category, severity, rule, points):
    assert calculate_risk([issue(category, severity, rule)], 1, 1)[0] == points


@pytest.mark.parametrize(
    "files,lines,expected",
    [
        (15, 500, 0),
        (16, 500, 10),
        (1, 501, 10),
        (1, 1000, 10),
        (1, 1001, 20),
        (16, 1001, 30),
    ],
)
def test_size_penalties_do_not_stack_incorrectly(files, lines, expected):
    assert calculate_risk([], files, lines)[0] == expected


def test_score_is_uncapped():
    assert calculate_risk([issue("security", "critical")] * 10, 0, 0) == (150, "Critical")


def test_negative_score_is_invalid():
    with pytest.raises(ValueError):
        classify_risk(-1)
