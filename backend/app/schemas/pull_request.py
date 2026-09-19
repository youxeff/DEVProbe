from pydantic import BaseModel, Field


class PullRequestResponse(BaseModel):
    number: int
    title: str
    author: str | None
    state: str
    html_url: str
    created_at: str
    updated_at: str


class PullRequestsResponse(BaseModel):
    pulls: list[PullRequestResponse]


class ChangedFileResponse(BaseModel):
    filename: str
    status: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changes: int = Field(ge=0)
    patch: str | None = None


class ChangedFilesResponse(BaseModel):
    files: list[ChangedFileResponse]
