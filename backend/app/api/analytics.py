from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.analytics import AnalyticsResponse
from app.services import analytics_service

router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
def analytics(repository_id: Annotated[int | None, Query(gt=0)] = None):
    return analytics_service.summary(repository_id)
