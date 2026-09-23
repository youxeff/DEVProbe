"""Keep previous paths; all handlers delegate to the canonical implementation."""

from fastapi import APIRouter

from app.api import pull_requests, repositories
from app.schemas.pull_request import ChangedFilesResponse, PullRequestsResponse
from app.schemas.repository import CommitsResponse, ParsedRepositoryResponse, RepositoryResponse

router = APIRouter()

for path, endpoint, schema in [
    ("/repositories/parse-repo-url", repositories.parse_repo_url, ParsedRepositoryResponse),
    ("/repositories/repo/metadata", repositories.get_repo_metadata, RepositoryResponse),
    ("/repositories/repo/commits", repositories.get_repo_commits, CommitsResponse),
    ("/repositories/repo/pulls", pull_requests.get_repo_pulls, PullRequestsResponse),
    (
        "/repositories/repo/pulls/{pr_number}/files",
        pull_requests.get_pull_request_files,
        ChangedFilesResponse,
    ),
    ("/parse-repo-url", repositories.parse_repo_url, ParsedRepositoryResponse),
    ("/analyze", repositories.parse_repo_url, ParsedRepositoryResponse),
    ("/repo/metadata", repositories.get_repo_metadata, RepositoryResponse),
    ("/repo/commits", repositories.get_repo_commits, CommitsResponse),
    ("/repo/pulls", pull_requests.get_repo_pulls, PullRequestsResponse),
    ("/repo/pulls/{pr_number}/files", pull_requests.get_pull_request_files, ChangedFilesResponse),
]:
    router.add_api_route(path, endpoint, methods=["POST"], response_model=schema, deprecated=True)
