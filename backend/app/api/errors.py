import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import ScanExecutionError, ServiceError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, error: ServiceError):
        content = {"detail": error.message}
        if isinstance(error, ScanExecutionError):
            content.update(scan_id=error.scan_id, status="failed")
        return JSONResponse(
            status_code=error.status_code,
            content=content,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, error: RequestValidationError):
        # Default validation errors echo input, which can include pasted credentials.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()
                ]
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception):
        logger.error("request_failed error_type=%s", type(error).__name__)
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})
