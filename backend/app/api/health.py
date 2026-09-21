from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/health/ready")
def ready():
    from app.services.health_service import readiness

    return readiness()
