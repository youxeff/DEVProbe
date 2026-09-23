from fastapi import APIRouter

from app.services import billing_service

router = APIRouter()


@router.get("")
def status():
    return billing_service.status()


@router.post("/checkout")
def checkout():
    return billing_service.checkout()


@router.post("/portal")
def portal():
    return billing_service.portal()
