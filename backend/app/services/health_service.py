from sqlalchemy import text

from app.core.errors import ServiceError
from app.db.session import session_scope


def readiness():
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        raise ServiceError("Database is not ready.", 503) from None
    return {"status": "ok", "database": "ready"}
