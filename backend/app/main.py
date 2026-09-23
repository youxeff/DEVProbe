from fastapi import FastAPI

from app.api import (
    analytics,
    billing,
    compatibility,
    github,
    health,
    organizations,
    pull_requests,
    repositories,
    scans,
    users,
    webhooks,
)
from app.api.errors import register_error_handlers
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import IdentityMiddleware


def create_app() -> FastAPI:
    get_settings()  # Validate production configuration before accepting requests.
    configure_logging()
    app = FastAPI(
        title="DevProbe API",
        description="AI-assisted code review and CI quality platform.",
        version="0.1.0",
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
    app.include_router(pull_requests.router, prefix="/pull-requests", tags=["Pull Requests"])
    app.include_router(compatibility.router, tags=["Compatibility"])
    app.include_router(scans.router, prefix="/scans", tags=["Scans"])
    app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
    app.include_router(users.router, prefix="/auth", tags=["Authentication"])
    app.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
    app.include_router(github.router, prefix="/github", tags=["GitHub App"])
    app.include_router(billing.router, prefix="/billing", tags=["Billing"])
    app.add_middleware(IdentityMiddleware)
    register_error_handlers(app)

    return app


app = create_app()
