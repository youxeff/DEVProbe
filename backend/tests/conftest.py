import json
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db import session as db_session
from app.db.database import Base, build_engine
from app.db.memory_store import MemoryScanStore
from app.main import create_app
from app.services import github_service, scan_service

REPO_URL = "https://github.com/owner/repo"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_session, "get_engine", lambda: engine)
    monkeypatch.setattr(scan_service, "store", MemoryScanStore())
    monkeypatch.setattr(github_service, "get_settings", lambda: Settings())
    # Every automated test must explicitly opt into mocked upstream responses.
    monkeypatch.setattr(
        requests, "get", Mock(side_effect=AssertionError("Unexpected network call"))
    )
    yield
    engine.dispose()


@pytest.fixture
def client():
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def response():
    def build(body=None, status=200, headers=None, raw=None):
        result = requests.Response()
        result.status_code = status
        result.url = "https://api.github.com/repos/owner/repo"
        result.headers.update(headers or {})
        result._content = raw if raw is not None else json.dumps(body).encode()
        result._content_consumed = True
        return result

    return build


@pytest.fixture
def github_mock(monkeypatch):
    def install(*responses):
        mock = Mock(side_effect=responses)
        monkeypatch.setattr(requests, "get", mock)
        return mock

    return install


@pytest.fixture
def repository_data():
    return {
        "id": 42,
        "owner": {"login": "owner"},
        "name": "repo",
        "full_name": "owner/repo",
        "description": None,
        "html_url": REPO_URL,
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 2,
        "forks_count": 1,
        "open_issues_count": 3,
    }


@pytest.fixture
def pull_data():
    return {
        "number": 12,
        "title": "Change authentication",
        "user": {"login": "dev"},
        "state": "open",
        "html_url": REPO_URL + "/pull/12",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "head": {"sha": "a" * 40},
        "base": {"sha": "b" * 40},
        "changed_files": 1,
    }


@pytest.fixture
def file_data():
    return {
        "filename": "app.py",
        "status": "modified",
        "additions": 2,
        "deletions": 1,
        "changes": 3,
        "patch": '@@ -1 +1,2 @@\n-print("old")\n+print("new")\n+# TODO: tidy',
    }
