from urllib.parse import urlparse
from fastapi import HTTPException
from dotenv import load_dotenv
import os
import requests

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def github_headers():
    headers = {
        "Accept": "application/vnd.github+json"
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def parse_github_url(repo_url: str):
    parsed_url = urlparse(repo_url)

    if parsed_url.netloc != "github.com":
        raise ValueError("Only GitHub repository URLs are supported.")

    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL.")

    owner = path_parts[0]
    repo = path_parts[1].replace(".git", "")

    if not owner or not repo:
        raise ValueError("Invalid GitHub repository URL.")

    return owner, repo


def handle_github_response(response, not_found_message="GitHub resource not found."):
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=not_found_message)

    if response.status_code == 403:
        raise HTTPException(
            status_code=403,
            detail="GitHub API rate limit or permission issue."
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="GitHub API request failed."
        )

    return response.json()


def fetch_repo_metadata(repo_url: str):
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=github_headers())
    data = handle_github_response(response, "GitHub repository not found.")

    contributors = fetch_repo_contributors(repo_url)

    return {
        "owner": data["owner"]["login"],
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "html_url": data["html_url"],
        "default_branch": data["default_branch"],
        "language": data["language"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "contributors": contributors
    }


def fetch_repo_contributors(repo_url: str):
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    response = requests.get(url, headers=github_headers())
    contributors_data = handle_github_response(response, "GitHub contributors not found.")

    contributors_list = []

    for contributor in contributors_data:
        contributors_list.append({
            "login": contributor["login"],
            "avatar_url": contributor["avatar_url"],
            "contributions": contributor["contributions"]
        })

    return contributors_list


def fetch_repo_commits(repo_url: str):
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    response = requests.get(url, headers=github_headers())
    commits_data = handle_github_response(response, "GitHub repository not found.")

    commits_list = []

    for commit in commits_data:
        commits_list.append({
            "sha": commit["sha"],
            "author": commit["commit"]["author"]["name"],
            "message": commit["commit"]["message"],
            "date": commit["commit"]["author"]["date"]
        })

    return commits_list


def fetch_pull_requests(repo_url: str):
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    response = requests.get(url, headers=github_headers())
    pulls_data = handle_github_response(response, "GitHub repository not found.")

    pulls_list = []

    for pull in pulls_data:
        pulls_list.append({
            "number": pull["number"],
            "title": pull["title"],
            "author": pull["user"]["login"],
            "state": pull["state"],
            "html_url": pull["html_url"],
            "created_at": pull["created_at"],
            "updated_at": pull["updated_at"]
        })

    return pulls_list


def fetch_pr_files(repo_url: str, pr_number: int):
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=github_headers())

    files_data = handle_github_response(
        response,
        "GitHub repository or pull request not found."
    )

    files_list = []

    for file in files_data:
        files_list.append({
            "filename": file["filename"],
            "status": file["status"],
            "additions": file["additions"],
            "deletions": file["deletions"],
            "changes": file["changes"],
            "patch": file.get("patch")
        })

    return files_list