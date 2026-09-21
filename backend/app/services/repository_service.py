from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.errors import ServiceError
from app.db.session import session_scope
from app.models import PullRequest, Repository
from app.services import github_service


def upsert(session, model, values, keys, *, update=True):
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(model).values(**values)
    if update:
        statement = statement.on_conflict_do_update(
            index_elements=keys,
            set_={k: getattr(statement.excluded, k) for k in values if k not in keys},
        )
    else:
        statement = statement.on_conflict_do_nothing(index_elements=keys)
    session.execute(statement)
    return session.scalar(select(model).where(*(getattr(model, k) == values[k] for k in keys)))


def ensure_repository(session, repo_url, organization_id=None):
    owner, name = github_service.parse_github_url(repo_url)
    return upsert(
        session,
        Repository,
        {
            "scope_key": organization_id or 0,
            "organization_id": organization_id,
            "owner": owner,
            "name": name,
            "full_name": f"{owner}/{name}".lower(),
            "html_url": f"https://github.com/{owner}/{name}",
        },
        ["scope_key", "full_name"],
        update=False,
    )


def ensure_pull_request(session, repository_id, pr_number):
    return upsert(
        session,
        PullRequest,
        {"repository_id": repository_id, "github_pr_number": pr_number},
        ["repository_id", "github_pr_number"],
        update=False,
    )


def repository_dict(repo):
    return {
        key: getattr(repo, key)
        for key in (
            "id",
            "github_repo_id",
            "owner",
            "name",
            "full_name",
            "html_url",
            "description",
            "default_branch",
            "language",
            "stars",
            "forks",
            "open_issues",
            "contributors",
        )
    }


def connect_repository(repo_url: str, organization_id: int | None = None) -> dict:
    metadata = github_service.fetch_repo_metadata(repo_url)
    with session_scope() as session:
        github_id = metadata.get("github_repo_id")
        repo = (
            session.scalar(
                select(Repository).where(
                    Repository.scope_key == (organization_id or 0),
                    Repository.github_repo_id == github_id,
                )
            )
            if github_id is not None
            else None
        )
        repo = repo or ensure_repository(session, repo_url, organization_id)
        for key, value in metadata.items():
            if hasattr(Repository, key):
                setattr(repo, key, value.lower() if key == "full_name" else value)
        session.flush()
        return {**metadata, "id": repo.id}


def get_repository(repository_id: int, organization_id: int | None = None) -> dict:
    with session_scope() as session:
        repo = session.scalar(
            select(Repository).where(
                Repository.id == repository_id, Repository.scope_key == (organization_id or 0)
            )
        )
        if repo is None:
            raise ServiceError("Repository not found.", 404)
        return repository_dict(repo)


def list_repositories(organization_id: int | None = None) -> list[dict]:
    with session_scope() as session:
        return [
            repository_dict(repo)
            for repo in session.scalars(
                select(Repository)
                .where(Repository.scope_key == (organization_id or 0))
                .order_by(Repository.updated_at.desc())
                .limit(200)
            )
        ]
