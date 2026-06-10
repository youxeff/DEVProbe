from pydantic import BaseModel


class ScanRequest(BaseModel):
    repo_url: str
    pr_number: int