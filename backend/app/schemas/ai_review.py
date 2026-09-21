from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ReviewItem = Annotated[str, Field(max_length=1000)]


class ReviewContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=3000)
    risks: list[ReviewItem] = Field(max_length=10)
    suggested_tests: list[ReviewItem] = Field(max_length=10)
    recommended_fixes: list[ReviewItem] = Field(max_length=10)


class AIReviewResponse(ReviewContent):
    model_name: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost: float | None = None
