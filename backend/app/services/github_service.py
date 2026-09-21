"""GitHub reads, normalization, and bounded transport behavior live here."""

import json
import re
from threading import Lock
from urllib.parse import urljoin, urlparse

import requests

from app.core.config import get_settings
from app.core.errors import InvalidRepositoryURL, ServiceError

API_ROOT = "https://api.github.com"


def github_headers(url: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DevProbe/0.1",
    }
    from app.core.context import installation_id, organization_id

    active = installation_id.get()
    if active is None and url and organization_id.get() is not None:
        from app.services.integration_service import installation_for_owner

        parts = urlparse(url).path.split("/")
        if len(parts) > 3 and parts[1] == "repos":
            linked = installation_for_owner(parts[2], organization_id.get())
            active = linked.github_installation_id if linked else None
    if active is not None:
        headers["Authorization"] = f"Bearer {installation_token(active)}"
        return headers
    # Shared development PAT must never authorize an organization-scoped request.
    token = get_settings().github_token if organization_id.get() is None else None
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
                headers=github_headers(url),
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


def fetch_file_at_commit(repo_url: str, filename: str, sha: str) -> str:
    """Read only bounded text at an immutable SHA; never follow download_url."""
    import base64
    from pathlib import PurePosixPath
    from urllib.parse import quote

    path = PurePosixPath(filename)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in filename
        or "\x00" in filename
        or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha)
    ):
        raise ServiceError("Invalid source file reference.", 422)
    data, _ = _get(
        _resource_url(repo_url, "/contents/" + quote(filename, safe="/")),
        "Source file not available at this commit.",
        {"ref": sha},
    )
    if (
        not isinstance(data, dict)
        or data.get("type") != "file"
        or data.get("size", 1_000_001) > 1_000_000
        or data.get("encoding") != "base64"
    ):
        raise ServiceError("Source file is too large or not supported.", 422)
    try:
        source = base64.b64decode(data["content"].replace("\n", ""), validate=True)
        if len(source) > 1_000_000 or b"\x00" in source:
            raise ValueError()
        return source.decode("utf-8")
    except (ValueError, KeyError, UnicodeDecodeError):
        raise ServiceError("Source file is not supported UTF-8 text.", 422) from None


def app_request(method: str, url: str, token: str, *, payload=None, params=None):
    """Explicit credentials for App/OAuth/Checks; never retry non-idempotent writes."""
    if url != "https://github.com/login/oauth/access_token":
        _trusted_api_url(url)
    try:
        with requests.request(
            method,
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
            params=params,
            timeout=(3, 10),
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code not in (200, 201, 202, 204):
                raise _error(response, "GitHub resource not found.")
            if response.status_code == 204:
                return {}, None
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > get_settings().github_max_response_bytes:
                    raise ServiceError("GitHub response exceeds size limit.", 422)
            try:
                return json.loads(body), response.links.get("next", {}).get("url")
            except (ValueError, UnicodeDecodeError):
                raise ServiceError("GitHub returned an invalid response.") from None
    except requests.RequestException:
        raise ServiceError("GitHub could not be reached.", 503) from None


def app_jwt() -> str:
    import time

    import jwt

    settings = get_settings()
    if not settings.github_app_id or not settings.github_private_key:
        raise ServiceError("GitHub App is not configured.", 503)
    now = int(time.time())
    try:
        return jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": settings.github_app_id},
            settings.github_private_key.get_secret_value().replace("\\n", "\n"),
            algorithm="RS256",
        )
    except Exception:
        raise ServiceError("GitHub App signing is not configured correctly.", 503) from None


# Short-lived installation tokens are never stored in the database.
_token_cache = {}
_token_lock = Lock()


def installation_token(installation_id: int) -> str:
    from datetime import UTC, datetime

    now = datetime.now(UTC).timestamp()
    with _token_lock:
        cached = _token_cache.get(installation_id)
        if cached and cached[1] > now + 60:
            return cached[0]
        data, _ = app_request(
            "POST",
            f"{API_ROOT}/app/installations/{installation_id}/access_tokens",
            app_jwt(),
            payload={},
        )
        expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
        if len(_token_cache) > 1000:
            _token_cache.clear()
        _token_cache[installation_id] = (data["token"], expires)
        return data["token"]


def verify_installation_owner(user_token: str, installation_id: int) -> dict:
    """Fail closed unless this GitHub user owns/administers the installation account."""
    user, _ = app_request("GET", f"{API_ROOT}/user", user_token)
    installation, _ = app_request(
        "GET", f"{API_ROOT}/app/installations/{installation_id}", app_jwt()
    )
    account = installation["account"]
    if account["type"] == "User":
        permitted = account["id"] == user["id"]
    elif account["type"] == "Organization":
        membership, _ = app_request(
            "GET", f"{API_ROOT}/user/memberships/orgs/{account['login']}", user_token
        )
        permitted = membership.get("state") == "active" and membership.get("role") == "admin"
    else:
        permitted = False
    if not permitted or installation.get("suspended_at"):
        raise ServiceError("GitHub account owner access is required for this installation.", 403)
    return {
        "github_installation_id": installation_id,
        "account_login": account["login"],
        "account_type": account["type"],
        "active": True,
    }


def exchange_oauth_code(code: str) -> str:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise ServiceError("GitHub OAuth is not configured.", 503)
    data, _ = app_request(
        "POST",
        "https://github.com/login/oauth/access_token",
        "",
        payload={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret.get_secret_value(),
            "code": code,
            "redirect_uri": settings.public_url + "/api/backend/github/callback",
        },
    )
    if not data.get("access_token"):
        raise ServiceError("GitHub authorization could not be completed.", 400)
    return data["access_token"]


def publish_check(
    repo_url: str, sha: str, external_id: str, output: dict, check_id: int | None = None
) -> int:
    from app.core.context import installation_id

    active = installation_id.get()
    if active is None:
        raise ServiceError("A GitHub App installation is required to publish checks.", 409)
    token = installation_token(active)
    if check_id is None:
        url = _resource_url(repo_url, f"/commits/{sha}/check-runs")
        for _ in range(get_settings().github_max_pages):
            data, next_url = app_request(
                "GET", url, token, params={"check_name": "DevProbe", "per_page": 100}
            )
            for row in data.get("check_runs", []):
                if (
                    row.get("external_id") == external_id
                    and str((row.get("app") or {}).get("id")) == get_settings().github_app_id
                ):
                    check_id = row["id"]
                    break
            if check_id or not next_url:
                break
            url = _trusted_api_url(next_url)
        else:
            raise ServiceError("GitHub checks exceed pagination limit.", 422)
    payload = {
        "name": "DevProbe",
        "status": "completed",
        "conclusion": output["conclusion"],
        "external_id": external_id,
        "output": {"title": output["title"], "summary": output["summary"]},
    }
    if check_id is not None:
        data, _ = app_request(
            "PATCH", _resource_url(repo_url, f"/check-runs/{check_id}"), token, payload=payload
        )
    else:
        data, _ = app_request(
            "POST",
            _resource_url(repo_url, "/check-runs"),
            token,
            payload={**payload, "head_sha": sha},
        )
    return data["id"]
