from typing import Annotated

from fastapi import APIRouter, Path

from app.schemas.pull_request import ChangedFilesResponse, PullRequestsResponse
from app.schemas.repository import RepoUrlRequest
from app.services import github_service

router = APIRouter()


@router.post("", response_model=PullRequestsResponse)
def get_repo_pulls(payload: RepoUrlRequest):
    return {"pulls": github_service.fetch_pull_requests(payload.repo_url)}


@router.post("/{pr_number}/files", response_model=ChangedFilesResponse)
def get_pull_request_files(pr_number: Annotated[int, Path(gt=0)], payload: RepoUrlRequest):
    return {"files": github_service.fetch_pr_files(payload.repo_url, pr_number)}
