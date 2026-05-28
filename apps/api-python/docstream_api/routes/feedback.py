import logging

from fastapi import APIRouter

from docstream_api.database import get_stats, insert_feedback
from docstream_api.models.schemas import FeedbackCreate, FeedbackResponse, FeedbackStats

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


@router.post("/api/v2/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackCreate) -> FeedbackResponse:
    """Store user feedback for a conversion job.

    Always returns ``success=True`` — feedback must never break the user flow.
    """
    try:
        feedback_id = insert_feedback(feedback.model_dump())
        logger.info(
            "Feedback stored: job=%s rating=%d",
            feedback.job_id,
            feedback.emoji_rating,
        )
        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
            feedback_id=feedback_id,
        )
    except Exception as exc:
        logger.error("Failed to store feedback: %s", exc)
        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!",
            feedback_id=None,
        )


@router.get("/api/v2/feedback/stats", response_model=FeedbackStats)
async def feedback_stats() -> FeedbackStats:
    """Return aggregated feedback statistics."""
    try:
        stats = get_stats()
        return FeedbackStats(**stats)
    except Exception as exc:
        logger.error("Failed to get feedback stats: %s", exc)
        return FeedbackStats(
            total_count=0,
            average_rating=0.0,
            rating_distribution={},
            recent_comments=[],
        )
