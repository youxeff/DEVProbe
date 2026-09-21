"""Request/worker identity, established only by trusted application code."""

from contextlib import contextmanager
from contextvars import ContextVar

organization_id: ContextVar[int | None] = ContextVar("organization_id", default=None)
user_id: ContextVar[int | None] = ContextVar("user_id", default=None)
role: ContextVar[str | None] = ContextVar("role", default=None)
installation_id: ContextVar[int | None] = ContextVar("installation_id", default=None)


@contextmanager
def organization_scope(value: int | None):
    token = organization_id.set(value)
    try:
        yield
    finally:
        organization_id.reset(token)
