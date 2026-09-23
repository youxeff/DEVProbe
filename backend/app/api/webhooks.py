from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.core.errors import ServiceError
from app.services import billing_service, webhook_service

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > webhook_service.MAX_BODY:
            raise ServiceError("Webhook body exceeds the size limit.", 413)
    return await run_in_threadpool(
        billing_service.webhook, bytes(body), request.headers.get("stripe-signature", "")
    )


@router.post("/github", status_code=202)
async def github_webhook(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > webhook_service.MAX_BODY:
            raise ServiceError("Webhook body exceeds the size limit.", 413)
    return await run_in_threadpool(
        webhook_service.receive,
        bytes(body),
        request.headers.get("x-hub-signature-256", ""),
        request.headers.get("x-github-event", ""),
        request.headers.get("x-github-delivery", ""),
    )
