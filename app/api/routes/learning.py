"""
Learning System API Routes
Endpoints for feedback-driven knowledge base improvements
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID

from app.core.dependencies import get_current_user
from app.models.draft_document import (
    GenerateDraftRequest,
    GenerateDraftResponse,
    DraftDocumentReview
)
from app.services.learning_service import (
    get_feedback_insights,
    generate_draft_from_feedback,
    get_pending_drafts,
    approve_draft,
    reject_draft
)
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/insights")
async def get_insights(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    GET /api/v1/learning/insights?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

    Get feedback patterns and suggested improvements
    Defaults to last 30 days if no dates provided

    Query Parameters:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    """
    try:
        insights = await get_feedback_insights(start_date=start_date, end_date=end_date)
        return insights
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(
    request: GenerateDraftRequest,
    current_user = Depends(get_current_user)
):
    """
    POST /api/v1/learning/generate-draft

    Generate knowledge base draft from feedback using LLM

    Body:
    {
        "feedback_ids": [UUID, ...],
        "query_pattern": "Pricing Questions",
        "category": "general",
        "additional_context": "..."
    }
    """
    try:
        result = await generate_draft_from_feedback(
            feedback_ids=request.feedback_ids,
            query_pattern=request.query_pattern,
            category=request.category,
            additional_context=request.additional_context
        )

        if result.get("success"):
            return GenerateDraftResponse(
                success=True,
                message=result["message"],
                draft_id=result.get("draft_id"),
                draft=result.get("draft")
            )
        else:
            return GenerateDraftResponse(
                success=False,
                message=result.get("message", "Failed to generate draft")
            )

    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts")
async def list_drafts(
    status: str = "pending",
    limit: int = 20,
    offset: int = 0,
    current_user = Depends(get_current_user)
):
    """
    GET /api/v1/learning/drafts?status=pending&limit=20&offset=0

    List draft documents (pending, approved, rejected)
    """
    try:
        if status == "pending":
            result = await get_pending_drafts(limit=limit, offset=offset)
            return result
        else:
            # TODO: Add support for other statuses
            return {"drafts": [], "total": 0}

    except Exception as e:
        logger.error(f"Error listing drafts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/approve")
async def approve_draft_endpoint(
    draft_id: UUID,
    review: DraftDocumentReview,
    auto_publish: bool = True,
    current_user = Depends(get_current_user)
):
    """
    POST /api/v1/learning/drafts/{id}/approve?auto_publish=true

    Approve draft document and optionally auto-publish to knowledge base

    Query Parameters:
        auto_publish: If true, automatically publishes draft to knowledge base (default: true)

    Body:
    {
        "status": "approved",
        "review_notes": "Looks good!"
    }

    Response:
    {
        "success": true,
        "message": "Draft approved and published to knowledge base",
        "draft": {...},
        "published": true,
        "document_id": "uuid"
    }
    """
    try:
        result = await approve_draft(
            draft_id=draft_id,
            reviewed_by=UUID(current_user["id"]),
            review_notes=review.review_notes,
            auto_publish=auto_publish
        )

        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/reject")
async def reject_draft_endpoint(
    draft_id: UUID,
    review: DraftDocumentReview,
    current_user = Depends(get_current_user)
):
    """
    POST /api/v1/learning/drafts/{id}/reject

    Reject draft document

    Body:
    {
        "status": "rejected",
        "review_notes": "Needs more detail"
    }
    """
    try:
        result = await reject_draft(
            draft_id=draft_id,
            reviewed_by=UUID(current_user["id"]),
            review_notes=review.review_notes
        )

        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/drafts/{draft_id}")
async def update_draft_endpoint(
    draft_id: UUID,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    PUT /api/v1/learning/drafts/{id}

    Update draft document content, title, or category

    Body:
    {
        "title": "Updated Title",
        "content": "Updated content...",
        "category": "updated-category"
    }
    """
    try:
        from app.core.database import get_supabase_client

        client = get_supabase_client()

        # Build update dict with only provided fields
        updates = {}
        if title is not None:
            updates["title"] = title
        if content is not None:
            updates["content"] = content
        if category is not None:
            updates["category"] = category

        if not updates:
            raise HTTPException(status_code=400, detail="No update fields provided")

        # Update the draft
        result = client.table("draft_documents").update(updates).eq(
            "id", str(draft_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Draft not found")

        return {
            "success": True,
            "message": "Draft updated successfully",
            "draft": result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/drafts/{draft_id}")
async def delete_draft_endpoint(
    draft_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    DELETE /api/v1/learning/drafts/{id}

    Delete draft document

    This permanently deletes the draft from the database.
    """
    try:
        from app.core.database import get_supabase_client

        client = get_supabase_client()

        # Delete the draft
        result = client.table("draft_documents").delete().eq(
            "id", str(draft_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Draft not found")

        return {
            "success": True,
            "message": "Draft deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-job")
async def trigger_learning_job(
    current_user = Depends(get_current_user)
):
    """
    POST /api/v1/learning/trigger-job

    Manually trigger the weekly learning job for testing/admin use
    This analyzes feedback and auto-generates drafts for critical patterns (10+ occurrences)
    """
    try:
        from app.services.scheduler import trigger_learning_job_manually
        result = await trigger_learning_job_manually()
        return result
    except Exception as e:
        logger.error(f"Error triggering learning job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
