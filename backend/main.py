from fastapi import FastAPI , HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse

app = FastAPI(title="DEVProbe API")


class URLRequest(BaseModel):
    repo_url: str


@app.get("/health")
def health_check():
    return {"status": "ok"}

def prase_github_URL (repo_url : str) : 
    prased_url = urlparse(repo_url)
    if prased_url.netloc != "github.com" :
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    path_parts = prased_url.path.strip("/").split("/")

    if len(path_parts) < 2 :
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner, repo = path_parts[0], path_parts[1]
    return owner, repo


@app.post("/analyze")
def analyze_repository(request: URLRequest):
    try:
        owner, repo = prase_github_URL(request.repo_url)
        # Here you would add the logic to analyze the repository using the owner and repo variables
        # For demonstration, we will just return the owner and repo
        return {"owner": owner, "repo": repo}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))