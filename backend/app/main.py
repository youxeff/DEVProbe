from fastapi import FastAPI

from app.api import health
from app.api import repositories
from app.api import pull_requests
from app.api import scans


def create_app() -> FastAPI:
    app = FastAPI(
        title="DevProbe API",
        description="AI-assisted code review and CI quality platform.",
        version="0.1.0",
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
    app.include_router(pull_requests.router, prefix="/pull-requests", tags=["Pull Requests"])
    app.include_router(scans.router, prefix="/scans", tags=["Scans"])

    return app


app = create_app()