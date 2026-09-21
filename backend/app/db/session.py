from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.database import get_engine


@contextmanager
def session_scope():
    with Session(get_engine(), expire_on_commit=False) as session, session.begin():
        yield session
