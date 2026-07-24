"""HTTP routes for the reviews resource.

Only HTTP concerns live here — routing, status codes, and translating
between API schemas (`app.api.schemas`) and the `ReviewService` call that
actually runs or looks up a review (see `.cursor/rules/backend.mdc`: "Keep
HTTP concerns ... inside the API layer only"). No workflow/orchestration
logic is implemented in these route functions; it is entirely delegated to
`ReviewService`.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_review_service
from app.api.schemas import ReviewCreateRequest, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    request: ReviewCreateRequest,
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Run a new review synchronously and return its full workflow output."""
    result = review_service.run_review(
        target_reference=request.target_reference,
        target_path=Path(request.target_path),
        code=request.code,
    )
    return ReviewResponse.from_run_result(result)


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: UUID,
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    """Return a previously persisted review, or 404 if it does not exist."""
    review = review_service.get_review(review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found: {review_id}",
        )
    return ReviewResponse.from_review(review)
