from pydantic import BaseModel


class RepoUrlRequest(BaseModel):
    repo_url: str