"""Only for the local queue integration test."""

from app.workers.celery_app import celery_app as celery_app
from tests.e2e_server import app as app
