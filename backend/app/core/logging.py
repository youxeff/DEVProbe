import json
import logging


class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        for key in (
            "request_id",
            "method",
            "route",
            "organization_id",
            "status",
            "duration_seconds",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        # Deliberately omit exception repr, request bodies, query strings and headers.
        return json.dumps(payload)


def configure_logging():
    logger = logging.getLogger("app")
    request_logger = logging.getLogger("devprobe.requests")
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJSONFormatter())
    for target in (logger, request_logger):
        if not target.handlers:
            target.addHandler(handler)
        target.setLevel(logging.INFO)
        target.propagate = False
