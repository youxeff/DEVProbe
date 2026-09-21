import pytest

REPO = {"repo_url": "https://github.com/owner/repo"}


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/repositories/parse-url",
        "/repositories/parse-repo-url",
        "/parse-repo-url",
        "/analyze",
    ],
)
def test_parse_aliases(client, path):
    result = client.post(path, json=REPO)
    assert result.status_code == 200
    assert result.json() == {"owner": "owner", "repo": "repo"}


@pytest.mark.parametrize(
    "path",
    [
        "/repositories/metadata",
        "/repositories/repo/metadata",
        "/repo/metadata",
    ],
)
def test_metadata_preserves_contract(client, response, github_mock, repository_data, path):
    contributor = {"login": "dev", "avatar_url": "https://example.com/avatar", "contributions": 2}
    github_mock(response(repository_data), response([contributor]))
    result = client.post(path, json=REPO)
    assert result.status_code == 200
    assert result.json() == {
        "id": 1,
        "github_repo_id": 42,
        "owner": "owner",
        "name": "repo",
        "full_name": "owner/repo",
        "description": None,
        "html_url": REPO["repo_url"],
        "default_branch": "main",
        "language": "Python",
        "stars": 2,
        "forks": 1,
        "open_issues": 3,
        "contributors": [contributor],
    }


@pytest.mark.parametrize(
    "path",
    [
        "/repositories/commits",
        "/repositories/repo/commits",
        "/repo/commits",
    ],
)
def test_commits_contract(client, response, github_mock, path):
    github_mock(response([{"sha": "abc", "commit": {"author": None, "message": "fix"}}]))
    result = client.post(path, json=REPO)
    assert result.status_code == 200
    assert result.json() == {
        "commits": [{"sha": "abc", "author": None, "message": "fix", "date": None}]
    }


@pytest.mark.parametrize("path", ["/pull-requests", "/repositories/repo/pulls", "/repo/pulls"])
def test_pull_aliases(client, response, github_mock, pull_data, path):
    github_mock(response([pull_data]))
    result = client.post(path, json=REPO)
    assert result.status_code == 200
    assert result.json()["pulls"][0] == {
        k: v
        for k, v in {**pull_data, "author": "dev"}.items()
        if k not in ("user", "head", "base", "changed_files")
    }


@pytest.mark.parametrize(
    "path",
    [
        "/pull-requests/12/files",
        "/repositories/repo/pulls/12/files",
        "/repo/pulls/12/files",
    ],
)
def test_file_aliases(client, response, github_mock, file_data, path):
    github_mock(response([file_data]))
    result = client.post(path, json=REPO)
    assert result.status_code == 200
    assert result.json() == {"files": [file_data]}


@pytest.mark.parametrize("path", ["/repositories/metadata", "/pull-requests", "/repo/commits"])
def test_invalid_url_is_400(client, path):
    result = client.post(path, json={"repo_url": "https://gitlab.com/o/r"})
    assert result.status_code == 400


def test_rate_limit_reaches_api(client, response, github_mock):
    github_mock(response({}, 403, {"Retry-After": "60"}))
    result = client.post("/pull-requests", json=REPO)
    assert result.status_code == 429
    assert result.headers["Retry-After"] == "60"


def test_invalid_pr_and_missing_body(client):
    assert client.post("/pull-requests/0/files", json=REPO).status_code == 422
    result = client.post("/repositories/metadata", json={"repo_url": {"secret": "do-not-echo"}})
    assert result.status_code == 422
    assert "do-not-echo" not in result.text


def test_unexpected_error_is_sanitized(client, github_mock):
    github_mock(RuntimeError("sensitive exception"))
    result = client.post("/pull-requests", json=REPO)
    assert result.status_code == 500
    assert result.json() == {"detail": "An internal error occurred."}
