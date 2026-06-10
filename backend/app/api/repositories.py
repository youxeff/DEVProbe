from fastapi import APIRouter, HTTPException
from app.schemas.repository import RepoUrlRequest
from app.services.github_service import (
    parse_github_url,
    fetch_repo_metadata,
    fetch_repo_commits,
    fetch_pull_requests,
    fetch_pr_files
)

router = APIRouter()


@router.post("/parse-repo-url")
def parse_repo_url(payload: RepoUrlRequest):
    try:
        owner, repo = parse_github_url(payload.repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "owner": owner,
        "repo": repo
    }


@router.post("/repo/metadata")
def get_repo_metadata(payload: RepoUrlRequest):
    return fetch_repo_metadata(payload.repo_url)


@router.post("/repo/commits")
def get_repo_commits(payload: RepoUrlRequest):
    commits = fetch_repo_commits(payload.repo_url)

    return {
        "commits": commits
    }


@router.post("/repo/pulls")
def get_repo_pulls(payload: RepoUrlRequest):
    pulls = fetch_pull_requests(payload.repo_url)

    return {
        "pulls": pulls
    }


@router.post("/repo/pulls/{pr_number}/files")
def get_pull_request_files(pr_number: int, payload: RepoUrlRequest):
    files = fetch_pr_files(payload.repo_url, pr_number)

    return {
        "files": files
    }