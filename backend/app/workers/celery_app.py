from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("devprobe", broker=settings.redis_url, include=["app.workers.scan_worker"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=660,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    broker_transport_options={
        "visibility_timeout": 900,
        "socket_timeout": 3,
        "socket_connect_timeout": 3,
    },
    task_publish_retry=False,
    worker_max_tasks_per_child=25,
    beat_schedule={"recover-pending-scans": {"task": "devprobe.recover_scans", "schedule": 30.0}},
)
