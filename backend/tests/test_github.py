import pytest
import requests

from app.core.config import Settings
from app.core.errors import ServiceError
from app.services import github_service as github

REPO = "https://github.com/owner/repo"


@pytest.mark.parametrize(
    "url,expected",
    [
        (REPO, ("owner", "repo")),
        (REPO + "/", ("owner", "repo")),
        (REPO + ".git", ("owner", "repo")),
        (REPO + ".git/", ("owner", "repo")),
        ("https://github.com/vercel/next.js", ("vercel", "next.js")),
        ("https://github.com/owner/repo.git.tools", ("owner", "repo.git.tools")),
        (REPO + "/pull/12", ("owner", "repo")),
    ],
)
def test_parser(url, expected):
    assert github.parse_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/o/r",
        "https://google.com/o/r",
        "https://github.com/",
        "https://github.com/o",
        "https://github.com//r",
        "https://github.com/o/.git",
        "https://github.com/o/..",
        "https://github.com/o/r%2fprivate",
        "https://github.com.evil.example/o/r",
        "https://secret@github.com/o/r",
        "https://github.com:443/o/r",
        "//github.com/o/r",
        "https://[broken/o/r",
    ],
)
def test_parser_rejects_bad_urls(url):
    with pytest.raises(ValueError):
        github.parse_github_url(url)


def test_token_only_in_outbound_headers(monkeypatch):
    config = Settings(github_token="test-only-credential")
    monkeypatch.setattr(github, "get_settings", lambda: config)
    assert github.github_headers()["Authorization"] == "Bearer test-only-credential"
    assert "test-only-credential" not in repr(config)


@pytest.mark.parametrize(
    "status,headers,expected",
    [
        (401, {}, 401),
        (403, {}, 403),
        (404, {}, 404),
        (429, {}, 429),
        (403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234"}, 429),
        (403, {"Retry-After": "60"}, 429),
        (422, {}, 422),
    ],
)
def test_error_mapping(response, github_mock, status, headers, expected):
    mock = github_mock(response({"message": "sensitive upstream body"}, status, headers))
    with pytest.raises(ServiceError) as caught:
        github.fetch_pr_files(REPO, 12)
    assert caught.value.status_code == expected
    assert "sensitive" not in str(caught.value)
    assert mock.call_count == 1


def test_all_pages_and_missing_patch(response, github_mock, file_data):
    second = {**file_data, "filename": "image.png"}
    second.pop("patch")
    next_url = "https://api.github.com/repos/owner/repo/pulls/12/files?page=2"
    mock = github_mock(
        response([file_data], headers={"Link": f'<{next_url}>; rel="next"'}), response([second])
    )
    files = github.fetch_pr_files(REPO, 12)
    assert len(files) == 2
    assert files[0]["patch"] == file_data["patch"]
    assert files[1]["patch"] is None
    assert mock.call_args_list[0].kwargs["timeout"] == (3, 10)
    assert mock.call_args_list[1].args == (next_url,)
    assert mock.call_args_list[1].kwargs["params"] is None


@pytest.mark.parametrize(
    "suffix,method",
    [
        ("contributors", github.fetch_repo_contributors),
        ("commits", github.fetch_repo_commits),
        ("pulls", github.fetch_pull_requests),
    ],
)
def test_pagination_for_other_lists(response, github_mock, suffix, method):
    next_url = f"https://api.github.com/repos/owner/repo/{suffix}?page=2"
    mock = github_mock(response([], headers={"Link": f'<{next_url}>; rel="next"'}), response([]))
    assert method(REPO) == []
    assert mock.call_count == 2


@pytest.mark.parametrize("header", ["Link", "Location"])
def test_external_continuations_never_receive_token(response, github_mock, header):
    url = "https://attacker.example/collect"
    value = f'<{url}>; rel="next"' if header == "Link" else url
    mock = github_mock(response([], 200 if header == "Link" else 301, {header: value}))
    with pytest.raises(ServiceError, match="unsafe"):
        github.fetch_pr_files(REPO, 12)
    assert mock.call_count == 1


def test_safe_repository_redirect(response, github_mock):
    mock = github_mock(
        response(None, 301, {"Location": "/repositories/123/pulls/12/files"}), response([])
    )
    assert github.fetch_pr_files(REPO, 12) == []
    assert mock.call_args.args[0] == "https://api.github.com/repositories/123/pulls/12/files"


def test_pagination_limit_is_explicit(monkeypatch, response, github_mock):
    monkeypatch.setattr(github, "get_settings", lambda: Settings(github_max_pages=1))
    github_mock(response([], headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'}))
    with pytest.raises(ServiceError, match="pagination limit"):
        github.fetch_pr_files(REPO, 12)


def test_transient_retry_is_bounded(github_mock):
    mock = github_mock(requests.Timeout("private request"), requests.Timeout("private request"))
    with pytest.raises(ServiceError) as caught:
        github.fetch_pr_files(REPO, 12)
    assert caught.value.status_code == 503
    assert "private" not in str(caught.value)
    assert mock.call_count == 2


def test_retry_recovers(response, github_mock):
    mock = github_mock(response(None, 503), response([]))
    assert github.fetch_pr_files(REPO, 12) == []
    assert mock.call_count == 2


def test_invalid_json(response, github_mock):
    github_mock(response(raw=b"not-json sensitive data"))
    with pytest.raises(ServiceError, match="invalid response"):
        github.fetch_pr_files(REPO, 12)


def test_response_size_limit(monkeypatch, response, github_mock):
    monkeypatch.setattr(github, "get_settings", lambda: Settings(github_max_response_bytes=1024))
    github_mock(response(raw=b"x" * 2048))
    with pytest.raises(ServiceError, match="size limit"):
        github.fetch_pr_files(REPO, 12)


def test_no_content(response, github_mock):
    github_mock(response(status=204))
    assert github.fetch_repo_contributors(REPO) == []
