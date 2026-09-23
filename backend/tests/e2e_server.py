"""Browser test server: real routes/database/analyzers, deterministic GitHub boundary."""

import json
import os

from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.core.errors import ServiceError
from app.main import app as app
from app.services import ai_service, github_service

os.environ["EXTERNAL_ANALYZERS"] = ""
get_settings.cache_clear()

REPO = "https://github.com/devprobe-fixtures/review-lab"
PULL = {
    "number": 12,
    "title": "Tighten authentication validation",
    "user": {"login": "alex"},
    "state": "open",
    "html_url": REPO + "/pull/12",
    "created_at": "2026-09-18T10:00:00Z",
    "updated_at": "2026-09-20T12:00:00Z",
    "head": {"sha": "a" * 40, "ref": "fix/auth"},
    "base": {"sha": "b" * 40, "ref": "main"},
    "changed_files": 2,
}
FILES = [
    {
        "filename": "src/auth.py",
        "status": "modified",
        "additions": 4,
        "deletions": 1,
        "changes": 5,
        "patch": "@@ -1 +1,4 @@\n-pass\n"
        "+password = 'test-fixture-only'\n+print('debug')\n"
        "+# TODO: update validation\n+enabled = True",
    },
    {
        "filename": "README.md",
        "status": "modified",
        "additions": 1,
        "deletions": 0,
        "changes": 1,
        "patch": "@@ -0,0 +1 @@\n+Authentication changes",
    },
]


def github_response(url, message, params=None):
    if "/missing/" in url:
        raise ServiceError("GitHub repository not found.", 404)
    if url.endswith("/files"):
        return FILES, None
    if "/pulls/" in url:
        return PULL, None
    if url.endswith("/pulls"):
        return [PULL], None
    if url.endswith("/contributors"):
        return [{"login": "alex", "avatar_url": None, "contributions": 21}], None
    return {
        "id": 9001,
        "owner": {"login": "devprobe-fixtures"},
        "name": "review-lab",
        "full_name": "devprobe-fixtures/review-lab",
        "description": "A controlled repository for testing the complete review workflow.",
        "html_url": REPO,
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 24,
        "forks_count": 3,
        "open_issues_count": 2,
    }, None


github_service._get = github_response

# Controlled provider response for browser rendering; never used by app.main.


ai_service.get_settings = lambda: Settings(ai_enabled=True, openai_api_key=SecretStr("test-only"))
ai_service._send = lambda *args: {
    "status": "completed",
    "usage": {"input_tokens": 100, "output_tokens": 80},
    "output": [
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": json.dumps(
                        {
                            "summary": "This fixture changes authentication code.",
                            "risks": ["Application changes have no corresponding test additions."],
                            "suggested_tests": ["Test the changed validation paths."],
                            "recommended_fixes": ["Review the possible secret and debug output."],
                        }
                    ),
                }
            ],
        }
    ],
}
