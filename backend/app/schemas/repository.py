from pydantic import BaseModel, Field


class RepoUrlRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=2048)


class ParsedRepositoryResponse(BaseModel):
    owner: str
    repo: str


class ContributorResponse(BaseModel):
    login: str | None
    avatar_url: str | None
    contributions: int


class RepositoryResponse(BaseModel):
    id: int | None = None
    github_repo_id: int | None = None
    owner: str
    name: str
    full_name: str
    description: str | None
    html_url: str
    default_branch: str | None
    language: str | None
    stars: int
    forks: int
    open_issues: int
    contributors: list[ContributorResponse]


class CommitResponse(BaseModel):
    sha: str
    author: str | None
    message: str
    date: str | None


class CommitsResponse(BaseModel):
    commits: list[CommitResponse]
