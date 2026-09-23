from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.schemas.repository import (
    CommitsResponse,
    ParsedRepositoryResponse,
    RepositoryResponse,
    RepoUrlRequest,
)
from app.schemas.scan import ScanResponse
from app.services import github_service, repository_service, scan_service

router = APIRouter()


@router.post("/parse-url", response_model=ParsedRepositoryResponse)
def parse_repo_url(payload: RepoUrlRequest):
    owner, repo = github_service.parse_github_url(payload.repo_url)
    return {"owner": owner, "repo": repo}


@router.post("/metadata", response_model=RepositoryResponse)
def get_repo_metadata(payload: RepoUrlRequest):
    return repository_service.connect_repository(payload.repo_url)


@router.post("/commits", response_model=CommitsResponse)
def get_repo_commits(payload: RepoUrlRequest):
    return {"commits": github_service.fetch_repo_commits(payload.repo_url)}


@router.get("", response_model=list[RepositoryResponse])
def list_repositories():
    return repository_service.list_repositories()


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: Annotated[int, Path(gt=0)]):
    return repository_service.get_repository(repository_id)


@router.get("/{repository_id}/scans", response_model=list[ScanResponse])
def repository_scans(
    repository_id: Annotated[int, Path(gt=0)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    repository_service.get_repository(repository_id)
    return scan_service.store.history(repository_id, offset=offset, limit=limit)
