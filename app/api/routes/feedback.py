"""
Feedback API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.feedback import FeedbackCreate, FeedbackResponse
from app.core.database import get_supabase_client
from app.utils.logger import get_logger
from datetime import datetime, timedelta

router = APIRouter()
logger = get_logger(__name__)


async def trigger_realtime_learning_if_needed():
    """
    Background task to trigger real-time learning check

    Triggers after every 5 negative feedbacks to balance responsiveness and performance
    """
    try:
        from app.services.learning_service import realtime_learning_check

        client = get_supabase_client()

        # Check negative feedback count in last hour
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        recent_feedback = client.table("feedback").select("id", count="exact").eq(
            "rating", 0
        ).gte("created_at", one_hour_ago).execute()

        recent_count = recent_feedback.count if hasattr(recent_feedback, 'count') else 0

        # Trigger learning check after every 5 negative feedbacks
        if recent_count > 0 and recent_count % 5 == 0:
            logger.info(f"🚀 Triggering real-time learning check ({recent_count} negative feedbacks in last hour)")
            result = await realtime_learning_check()
            logger.info(f"Real-time learning result: {result.get('drafts_generated', 0)} drafts generated")
        else:
            logger.debug(f"Skipping real-time learning check ({recent_count} negative feedbacks, waiting for multiple of 5)")

    except Exception as e:
        logger.warning(f"Real-time learning check failed (non-critical): {e}")


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackCreate, background_tasks: BackgroundTasks):
    """
    Submit feedback for a message

    Public endpoint (no auth required)

    Real-time Learning:
    - Negative feedback (rating=0) triggers real-time learning check in background
    - Learning runs after every 5 negative feedbacks to balance responsiveness and performance
    - Generates drafts for patterns with 3+ occurrences in last 7 days
    """
    try:
        client = get_supabase_client()

        data = {
            "message_id": str(feedback.message_id),
            "rating": feedback.rating,
            "comment": feedback.comment,
            "created_at": datetime.utcnow().isoformat()
        }

        response = client.table("feedback").insert(data).execute()

        logger.info(f"Feedback submitted for message {feedback.message_id} (rating={feedback.rating})")

        # Trigger real-time learning check for negative feedback (non-blocking)
        if feedback.rating == 0:
            logger.info("👎 Negative feedback received - scheduling real-time learning check")
            background_tasks.add_task(trigger_realtime_learning_if_needed)

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!"
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
