from fastapi import APIRouter

from app.schemas.repository import (
    CommitsResponse,
    ParsedRepositoryResponse,
    RepositoryResponse,
    RepoUrlRequest,
)
from app.services import github_service

router = APIRouter()


@router.post("/parse-url", response_model=ParsedRepositoryResponse)
def parse_repo_url(payload: RepoUrlRequest):
    owner, repo = github_service.parse_github_url(payload.repo_url)
    return {"owner": owner, "repo": repo}


@router.post("/metadata", response_model=RepositoryResponse)
def get_repo_metadata(payload: RepoUrlRequest):
    return github_service.fetch_repo_metadata(payload.repo_url)


@router.post("/commits", response_model=CommitsResponse)
def get_repo_commits(payload: RepoUrlRequest):
    return {"commits": github_service.fetch_repo_commits(payload.repo_url)}
