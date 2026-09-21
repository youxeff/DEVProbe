"""GitHub reads, normalization, and bounded transport behavior live here."""

import json
import re
from urllib.parse import urljoin, urlparse

import requests

from app.core.config import get_settings
from app.core.errors import InvalidRepositoryURL, ServiceError

API_ROOT = "https://api.github.com"


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DevProbe/0.1",
    }
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token.get_secret_value()}"
    return headers


def parse_github_url(repo_url: str) -> tuple[str, str]:
    try:
        parsed = urlparse(repo_url.strip())
    except ValueError:
        raise InvalidRepositoryURL("Invalid GitHub repository URL.") from None
    if parsed.scheme not in ("https", "http") or parsed.netloc.lower() != "github.com":
        raise InvalidRepositoryURL("Only GitHub repository URLs are supported.")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise InvalidRepositoryURL("Invalid GitHub repository URL.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", owner)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo)
        or repo in (".", "..")
    ):
        raise InvalidRepositoryURL("Invalid GitHub repository URL.")
    # Nested GitHub URLs were accepted by the previous parser; keep that behavior.
    return owner, repo


def _trusted_api_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.fragment:
        raise ServiceError("GitHub returned an unsafe continuation URL.")
    return url


def _error(response: requests.Response, not_found_message: str) -> ServiceError:
    status = response.status_code
    headers = {}
    for name in ("Retry-After", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
        value = response.headers.get(name, "")
        if value.isdigit():
            headers[name] = value
    if status == 429 or (
        status == 403
        and (
            response.headers.get("X-RateLimit-Remaining") == "0"
            or "Retry-After" in response.headers
        )
    ):
        return ServiceError("GitHub API rate limit reached. Try again later.", 429, headers)
    if status == 404:
        return ServiceError(not_found_message, 404)
    if status == 401:
        return ServiceError("GitHub authentication failed. Check the server token.", 401)
    if status == 403:
        return ServiceError("GitHub denied access to this resource.", 403)
    if status in (409, 422):
        return ServiceError("GitHub could not process this request.", status)
    return ServiceError("GitHub API request failed.")


def _get(url: str, not_found_message: str, params: dict | None = None):
    settings = get_settings()
    # At most one retry on transient network/5xx errors, and three redirects.
    redirects = 0
    retries = 0
    while True:
        _trusted_api_url(url)
        try:
            response = requests.get(
                url,
                headers=github_headers(),
                params=params,
                timeout=(3, settings.github_timeout_seconds),
                allow_redirects=False,
                stream=True,
            )
            with response:
                if response.status_code in (301, 302, 303, 307, 308):
                    if redirects >= 3 or not response.headers.get("Location"):
                        raise ServiceError("GitHub returned too many or invalid redirects.")
                    url = _trusted_api_url(urljoin(response.url, response.headers["Location"]))
                    params = None
                    redirects += 1
                    continue
                if response.status_code in (502, 503, 504) and retries < 1:
                    retries += 1
                    continue
                if response.status_code == 204:
                    return [], None
                if response.status_code != 200:
                    raise _error(response, not_found_message)
                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > settings.github_max_response_bytes:
                        raise ServiceError(
                            "GitHub response exceeds the configured size limit.", 422
                        )
                try:
                    data = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    raise ServiceError("GitHub returned an invalid response.") from None
                return data, response.links.get("next", {}).get("url")
        except requests.RequestException:
            if retries < 1:
                retries += 1
                continue
            raise ServiceError("GitHub could not be reached. Try again later.", 503) from None


def _resource_url(repo_url: str, suffix: str = "") -> str:
    owner, repo = parse_github_url(repo_url)
    return f"{API_ROOT}/repos/{owner}/{repo}{suffix}"


def _list(repo_url: str, suffix: str, *, params: dict | None = None) -> list[dict]:
    url = _resource_url(repo_url, suffix)
    query = {"per_page": 100, **(params or {})}
    items = []
    visited = set()
    for _ in range(get_settings().github_max_pages):
        if url in visited:
            raise ServiceError("GitHub returned a pagination loop.")
        visited.add(url)
        data, next_url = _get(url, "GitHub repository or resource not found.", query)
        if not isinstance(data, list):
            raise ServiceError("GitHub returned an invalid list response.")
        items.extend(data)
        if not next_url:
            return items
        url, query = _trusted_api_url(next_url), None
    # Never quietly score or present a truncated dataset as complete.
    raise ServiceError("GitHub results exceed the configured pagination limit.", 422)


def fetch_repo_metadata(repo_url: str) -> dict:
    data, _ = _get(_resource_url(repo_url), "GitHub repository not found.")
    return {
        "owner": data["owner"]["login"],
        "github_repo_id": data.get("id"),
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "html_url": data["html_url"],
        "default_branch": data["default_branch"],
        "language": data["language"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "contributors": fetch_repo_contributors(repo_url),
    }


def fetch_repo_contributors(repo_url: str) -> list[dict]:
    return [
        {
            "login": row.get("login"),
            "avatar_url": row.get("avatar_url"),
            "contributions": row["contributions"],
        }
        for row in _list(repo_url, "/contributors")
    ]


def fetch_repo_commits(repo_url: str) -> list[dict]:
    commits = []
    for row in _list(repo_url, "/commits"):
        author = row["commit"].get("author") or {}
        commits.append(
            {
                "sha": row["sha"],
                "author": author.get("name"),
                "message": row["commit"]["message"],
                "date": author.get("date"),
            }
        )
    return commits


def _normalize_pull_request(row: dict) -> dict:
    return {
        "number": row["number"],
        "title": row["title"],
        "author": (row.get("user") or {}).get("login"),
        "state": row["state"],
        "html_url": row["html_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_pull_requests(repo_url: str) -> list[dict]:
    return [_normalize_pull_request(row) for row in _list(repo_url, "/pulls")]


def fetch_pull_request(repo_url: str, pr_number: int) -> dict:
    data, _ = _get(
        _resource_url(repo_url, f"/pulls/{pr_number}"),
        "GitHub repository or pull request not found.",
    )
    return {
        **_normalize_pull_request(data),
        "changed_files": data["changed_files"],
        "head_sha": data["head"]["sha"],
        "base_sha": data["base"]["sha"],
        "base_branch": data["base"].get("ref"),
        "head_branch": data["head"].get("ref"),
    }


def fetch_pr_files(repo_url: str, pr_number: int) -> list[dict]:
    return [
        {
            "filename": row["filename"],
            "status": row["status"],
            "additions": row["additions"],
            "deletions": row["deletions"],
            "changes": row["changes"],
            "patch": row.get("patch"),
        }
        for row in _list(repo_url, f"/pulls/{pr_number}/files")
    ]
