"""
API routes for soft delete operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID

from app.core.dependencies import get_current_user
from app.models.soft_delete import (
    SoftDeleteRequest,
    RecoverRequest,
    PermanentDeleteRequest,
    UpdateConversationRequest,
    UpdateMessageRequest,
    UpdateFeedbackRequest,
    DeletedItemsResponse,
    SoftDeleteResponse,
    RecoverResponse,
    PermanentDeleteResponse,
    UpdateResponse,
    CleanupResponse,
    DeletedItem
)
from app.services.soft_delete_service import SoftDeleteService

router = APIRouter(prefix="/soft-delete", tags=["Soft Delete"])


# ==================== Soft Delete Endpoints ====================

@router.delete("/conversation/{conversation_id}", response_model=SoftDeleteResponse)
async def soft_delete_conversation(
    conversation_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Soft delete a conversation and all related messages/feedback

    - Marks conversation as deleted
    - Sets deleted_at timestamp and deleted_by user
    - Cascades to all messages and feedback
    - Can be recovered within 30 days
    """
    try:
        result = await SoftDeleteService.soft_delete_conversation(
            conversation_id=conversation_id,
            user_id=UUID(current_user["id"])
        )
        return SoftDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["conversation_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/message/{message_id}", response_model=SoftDeleteResponse)
async def soft_delete_message(
    message_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Soft delete a single message and related feedback

    - Marks message as deleted
    - Sets deleted_at timestamp and deleted_by user
    - Cascades to feedback on this message
    - Can be recovered within 30 days
    """
    try:
        result = await SoftDeleteService.soft_delete_message(
            message_id=message_id,
            user_id=UUID(current_user["id"])
        )
        return SoftDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["message_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/feedback/{feedback_id}", response_model=SoftDeleteResponse)
async def soft_delete_feedback(
    feedback_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Soft delete feedback

    - Marks feedback as deleted
    - Sets deleted_at timestamp and deleted_by user
    - Can be recovered within 30 days
    """
    try:
        result = await SoftDeleteService.soft_delete_feedback(
            feedback_id=feedback_id,
            user_id=UUID(current_user["id"])
        )
        return SoftDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["feedback_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/draft/{draft_id}", response_model=SoftDeleteResponse)
async def soft_delete_draft(
    draft_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Soft delete a draft document

    - Marks draft as deleted
    - Sets deleted_at timestamp and deleted_by user
    - Can be recovered within 30 days
    """
    try:
        result = await SoftDeleteService.soft_delete_draft(
            draft_id=draft_id,
            user_id=UUID(current_user["id"])
        )
        return SoftDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["draft_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Recovery Endpoints ====================

@router.post("/conversation/{conversation_id}/recover", response_model=RecoverResponse)
async def recover_conversation(
    conversation_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Recover a soft-deleted conversation

    - Removes deleted_at timestamp
    - Recovers all related messages and feedback
    - Conversation becomes active again
    """
    try:
        result = await SoftDeleteService.recover_conversation(conversation_id)
        return RecoverResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["conversation_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/{message_id}/recover", response_model=RecoverResponse)
async def recover_message(
    message_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Recover a soft-deleted message

    - Removes deleted_at timestamp
    - Recovers related feedback
    - Message becomes active again
    """
    try:
        result = await SoftDeleteService.recover_message(message_id)
        return RecoverResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["message_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/{feedback_id}/recover", response_model=RecoverResponse)
async def recover_feedback(
    feedback_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Recover a soft-deleted feedback

    - Removes deleted_at timestamp
    - Feedback becomes active again
    """
    try:
        result = await SoftDeleteService.recover_feedback(feedback_id)
        return RecoverResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["feedback_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft/{draft_id}/recover", response_model=RecoverResponse)
async def recover_draft(
    draft_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Recover a soft-deleted draft

    - Removes deleted_at timestamp
    - Draft becomes active again
    """
    try:
        result = await SoftDeleteService.recover_draft(draft_id)
        return RecoverResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["draft_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Permanent Delete Endpoints ====================

@router.delete("/conversation/{conversation_id}/permanent", response_model=PermanentDeleteResponse)
async def permanent_delete_conversation(
    conversation_id: UUID,
    confirm: bool = Query(..., description="Must be true to confirm permanent deletion"),
    current_user = Depends(get_current_user)
):
    """
    Permanently delete a conversation (CANNOT BE RECOVERED)

    - Removes all data from database
    - Deletes all related messages and feedback
    - Cannot be undone
    - Requires confirmation

    **WARNING:** This action is irreversible!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required for permanent deletion"
        )

    try:
        result = await SoftDeleteService.permanent_delete_conversation(conversation_id)
        return PermanentDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["conversation_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/message/{message_id}/permanent", response_model=PermanentDeleteResponse)
async def permanent_delete_message(
    message_id: UUID,
    confirm: bool = Query(..., description="Must be true to confirm permanent deletion"),
    current_user = Depends(get_current_user)
):
    """
    Permanently delete a message (CANNOT BE RECOVERED)

    - Removes all data from database
    - Deletes related feedback
    - Cannot be undone
    - Requires confirmation

    **WARNING:** This action is irreversible!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required for permanent deletion"
        )

    try:
        result = await SoftDeleteService.permanent_delete_message(message_id)
        return PermanentDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["message_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/feedback/{feedback_id}/permanent", response_model=PermanentDeleteResponse)
async def permanent_delete_feedback(
    feedback_id: UUID,
    confirm: bool = Query(..., description="Must be true to confirm permanent deletion"),
    current_user = Depends(get_current_user)
):
    """
    Permanently delete feedback (CANNOT BE RECOVERED)

    - Removes all data from database
    - Cannot be undone
    - Requires confirmation

    **WARNING:** This action is irreversible!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required for permanent deletion"
        )

    try:
        result = await SoftDeleteService.permanent_delete_feedback(feedback_id)
        return PermanentDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["feedback_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/draft/{draft_id}/permanent", response_model=PermanentDeleteResponse)
async def permanent_delete_draft(
    draft_id: UUID,
    confirm: bool = Query(..., description="Must be true to confirm permanent deletion"),
    current_user = Depends(get_current_user)
):
    """
    Permanently delete a draft (CANNOT BE RECOVERED)

    - Removes all data from database
    - Cannot be undone
    - Requires confirmation

    **WARNING:** This action is irreversible!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required for permanent deletion"
        )

    try:
        result = await SoftDeleteService.permanent_delete_draft(draft_id)
        return PermanentDeleteResponse(
            success=result["success"],
            message=result["message"],
            item_id=result["draft_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Update Endpoints ====================

@router.put("/conversation/{conversation_id}", response_model=UpdateResponse)
async def update_conversation(
    conversation_id: UUID,
    request: UpdateConversationRequest,
    current_user = Depends(get_current_user)
):
    """
    Update conversation metadata

    - Updates specified fields
    - Sets updated_at timestamp and updated_by user
    """
    try:
        updates = {}
        if request.session_id is not None:
            updates["session_id"] = request.session_id

        result = await SoftDeleteService.update_conversation(
            conversation_id=conversation_id,
            user_id=UUID(current_user["id"]),
            updates=updates
        )
        return UpdateResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("conversation")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/message/{message_id}", response_model=UpdateResponse)
async def update_message(
    message_id: UUID,
    request: UpdateMessageRequest,
    current_user = Depends(get_current_user)
):
    """
    Update message content

    - Updates message text
    - Sets updated_at timestamp and updated_by user
    """
    try:
        result = await SoftDeleteService.update_message(
            message_id=message_id,
            user_id=UUID(current_user["id"]),
            content=request.content
        )
        return UpdateResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/feedback/{feedback_id}", response_model=UpdateResponse)
async def update_feedback(
    feedback_id: UUID,
    request: UpdateFeedbackRequest,
    current_user = Depends(get_current_user)
):
    """
    Update feedback rating or comment

    - Updates rating (0 or 1) or comment
    - Sets updated_at timestamp and updated_by user
    """
    try:
        result = await SoftDeleteService.update_feedback(
            feedback_id=feedback_id,
            user_id=UUID(current_user["id"]),
            rating=request.rating,
            comment=request.comment
        )
        return UpdateResponse(
            success=result["success"],
            message=result["message"],
            data=result.get("feedback")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== List Deleted Items ====================

@router.get("/items", response_model=DeletedItemsResponse)
async def get_deleted_items(
    item_type: Optional[str] = Query(None, description="Filter by type: conversation, message, feedback, or draft"),
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user = Depends(get_current_user)
):
    """
    Get list of all soft-deleted items

    - Returns deleted conversations, messages, feedback, and drafts
    - Supports filtering by type
    - Includes deletion metadata
    - Shows days remaining until permanent deletion (30 days)
    """
    try:
        from datetime import datetime, timedelta

        result = await SoftDeleteService.get_deleted_items(
            item_type=item_type,
            limit=limit,
            offset=offset
        )

        # Calculate days until permanent deletion for each item
        items = []
        for item in result["items"]:
            deleted_at = item.get("deleted_at")
            if deleted_at:
                if isinstance(deleted_at, str):
                    deleted_at = datetime.fromisoformat(deleted_at.replace('Z', '+00:00'))

                permanent_date = deleted_at + timedelta(days=30)
                days_remaining = max(0, (permanent_date - datetime.now(deleted_at.tzinfo)).days)
            else:
                days_remaining = 0

            items.append(DeletedItem(
                **item,
                days_until_permanent=days_remaining
            ))

        return DeletedItemsResponse(
            items=items,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Cleanup Endpoint ====================

@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_deleted_items(
    current_user = Depends(get_current_user)
):
    """
    Manually trigger cleanup of old deleted items

    - Permanently deletes items soft-deleted for 30+ days
    - This happens automatically via scheduled job
    - Manual trigger useful for testing or immediate cleanup
    - Returns count of items deleted
    """
    try:
        result = await SoftDeleteService.cleanup_old_deleted_items()
        return CleanupResponse(
            success=result["success"],
            message=result["message"],
            deleted_count=result["deleted_count"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
