"""
Soft Delete Service
Handles soft deletion, recovery, and permanent deletion of items
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import logging

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)


class SoftDeleteService:
    """Service for managing soft-deleted items"""

    @staticmethod
    async def soft_delete_conversation(
        conversation_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Soft delete a conversation and all related messages/feedback

        Args:
            conversation_id: UUID of conversation to delete
            user_id: UUID of user performing deletion

        Returns:
            Dict with success status and message
        """
        try:
            client = get_supabase_client()

            # Call the database function for soft delete
            result = client.rpc(
                'soft_delete_conversation',
                {
                    'p_conversation_id': str(conversation_id),
                    'p_user_id': str(user_id)
                }
            ).execute()

            return {
                "success": True,
                "message": "Conversation soft-deleted successfully",
                "conversation_id": str(conversation_id)
            }

        except Exception as e:
            logger.error(f"Error soft-deleting conversation {conversation_id}: {e}")
            raise


    @staticmethod
    async def soft_delete_message(
        message_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Soft delete a single message

        Args:
            message_id: UUID of message to delete
            user_id: UUID of user performing deletion

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Soft delete the message
            client.table("messages").update({
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": str(user_id)
            }).eq("id", str(message_id)).execute()

            # Soft delete related feedback
            client.table("feedback").update({
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": str(user_id)
            }).eq("message_id", str(message_id)).execute()

            return {
                "success": True,
                "message": "Message soft-deleted successfully",
                "message_id": str(message_id)
            }

        except Exception as e:
            logger.error(f"Error soft-deleting message {message_id}: {e}")
            raise


    @staticmethod
    async def soft_delete_feedback(
        feedback_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Soft delete feedback

        Args:
            feedback_id: UUID of feedback to delete
            user_id: UUID of user performing deletion

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            client.table("feedback").update({
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": str(user_id)
            }).eq("id", str(feedback_id)).execute()

            return {
                "success": True,
                "message": "Feedback soft-deleted successfully",
                "feedback_id": str(feedback_id)
            }

        except Exception as e:
            logger.error(f"Error soft-deleting feedback {feedback_id}: {e}")
            raise


    @staticmethod
    async def recover_conversation(conversation_id: UUID) -> Dict[str, Any]:
        """
        Recover a soft-deleted conversation

        Args:
            conversation_id: UUID of conversation to recover

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Call the database function for recovery
            result = client.rpc(
                'recover_conversation',
                {'p_conversation_id': str(conversation_id)}
            ).execute()

            return {
                "success": True,
                "message": "Conversation recovered successfully",
                "conversation_id": str(conversation_id)
            }

        except Exception as e:
            logger.error(f"Error recovering conversation {conversation_id}: {e}")
            raise


    @staticmethod
    async def recover_message(message_id: UUID) -> Dict[str, Any]:
        """
        Recover a soft-deleted message

        Args:
            message_id: UUID of message to recover

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Recover the message
            client.table("messages").update({
                "deleted_at": None,
                "deleted_by": None
            }).eq("id", str(message_id)).execute()

            # Recover related feedback
            client.table("feedback").update({
                "deleted_at": None,
                "deleted_by": None
            }).eq("message_id", str(message_id)).execute()

            return {
                "success": True,
                "message": "Message recovered successfully",
                "message_id": str(message_id)
            }

        except Exception as e:
            logger.error(f"Error recovering message {message_id}: {e}")
            raise


    @staticmethod
    async def recover_feedback(feedback_id: UUID) -> Dict[str, Any]:
        """
        Recover a soft-deleted feedback

        Args:
            feedback_id: UUID of feedback to recover

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            client.table("feedback").update({
                "deleted_at": None,
                "deleted_by": None
            }).eq("id", str(feedback_id)).execute()

            return {
                "success": True,
                "message": "Feedback recovered successfully",
                "feedback_id": str(feedback_id)
            }

        except Exception as e:
            logger.error(f"Error recovering feedback {feedback_id}: {e}")
            raise


    @staticmethod
    async def soft_delete_draft(
        draft_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Soft delete a draft document

        Args:
            draft_id: UUID of draft to delete
            user_id: UUID of user performing deletion

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            client.table("draft_documents").update({
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": str(user_id)
            }).eq("id", str(draft_id)).execute()

            return {
                "success": True,
                "message": "Draft soft-deleted successfully",
                "draft_id": str(draft_id)
            }

        except Exception as e:
            logger.error(f"Error soft-deleting draft {draft_id}: {e}")
            raise


    @staticmethod
    async def recover_draft(draft_id: UUID) -> Dict[str, Any]:
        """
        Recover a soft-deleted draft

        Args:
            draft_id: UUID of draft to recover

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            client.table("draft_documents").update({
                "deleted_at": None,
                "deleted_by": None
            }).eq("id", str(draft_id)).execute()

            return {
                "success": True,
                "message": "Draft recovered successfully",
                "draft_id": str(draft_id)
            }

        except Exception as e:
            logger.error(f"Error recovering draft {draft_id}: {e}")
            raise


    @staticmethod
    async def permanent_delete_conversation(conversation_id: UUID) -> Dict[str, Any]:
        """
        Permanently delete a conversation (cannot be recovered)

        Args:
            conversation_id: UUID of conversation to permanently delete

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Call the database function for permanent deletion
            result = client.rpc(
                'permanent_delete_conversation',
                {'p_conversation_id': str(conversation_id)}
            ).execute()

            return {
                "success": True,
                "message": "Conversation permanently deleted",
                "conversation_id": str(conversation_id)
            }

        except Exception as e:
            logger.error(f"Error permanently deleting conversation {conversation_id}: {e}")
            raise


    @staticmethod
    async def permanent_delete_message(message_id: UUID) -> Dict[str, Any]:
        """
        Permanently delete a message

        Args:
            message_id: UUID of message to permanently delete

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Check if message is soft-deleted
            message_check = client.table("messages").select("deleted_at").eq(
                "id", str(message_id)
            ).execute()

            if not message_check.data or not message_check.data[0].get("deleted_at"):
                raise ValueError("Message must be soft-deleted before permanent deletion")

            # Delete related feedback first
            client.table("feedback").delete().eq("message_id", str(message_id)).execute()

            # Delete the message
            client.table("messages").delete().eq("id", str(message_id)).execute()

            return {
                "success": True,
                "message": "Message permanently deleted",
                "message_id": str(message_id)
            }

        except Exception as e:
            logger.error(f"Error permanently deleting message {message_id}: {e}")
            raise


    @staticmethod
    async def permanent_delete_feedback(feedback_id: UUID) -> Dict[str, Any]:
        """
        Permanently delete feedback

        Args:
            feedback_id: UUID of feedback to permanently delete

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Check if feedback is soft-deleted
            feedback_check = client.table("feedback").select("deleted_at").eq(
                "id", str(feedback_id)
            ).execute()

            if not feedback_check.data or not feedback_check.data[0].get("deleted_at"):
                raise ValueError("Feedback must be soft-deleted before permanent deletion")

            # Delete the feedback
            client.table("feedback").delete().eq("id", str(feedback_id)).execute()

            return {
                "success": True,
                "message": "Feedback permanently deleted",
                "feedback_id": str(feedback_id)
            }

        except Exception as e:
            logger.error(f"Error permanently deleting feedback {feedback_id}: {e}")
            raise


    @staticmethod
    async def permanent_delete_draft(draft_id: UUID) -> Dict[str, Any]:
        """
        Permanently delete a draft

        Args:
            draft_id: UUID of draft to permanently delete

        Returns:
            Dict with success status
        """
        try:
            client = get_supabase_client()

            # Check if draft is soft-deleted
            draft_check = client.table("draft_documents").select("deleted_at").eq(
                "id", str(draft_id)
            ).execute()

            if not draft_check.data or not draft_check.data[0].get("deleted_at"):
                raise ValueError("Draft must be soft-deleted before permanent deletion")

            # Delete the draft
            client.table("draft_documents").delete().eq("id", str(draft_id)).execute()

            return {
                "success": True,
                "message": "Draft permanently deleted",
                "draft_id": str(draft_id)
            }

        except Exception as e:
            logger.error(f"Error permanently deleting draft {draft_id}: {e}")
            raise


    @staticmethod
    async def get_deleted_items(
        item_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get list of deleted items

        Note: Messages are excluded from the trash view since they're part of conversations.
        When a conversation is deleted, all its messages are cascaded but only the conversation
        appears in trash. Restoring the conversation restores all messages automatically.

        Args:
            item_type: Filter by type (conversation, feedback, draft) or None for all
                       Note: 'message' type is not supported as messages don't appear individually
            limit: Number of items to return
            offset: Pagination offset

        Returns:
            Dict with deleted items list and total count
        """
        try:
            client = get_supabase_client()

            # Query the deleted_items_view
            query = client.table("deleted_items_view").select("*")

            # ALWAYS exclude messages from trash - they're represented by their parent conversation
            query = query.neq("item_type", "message")

            if item_type:
                # Validate item_type
                if item_type == "message":
                    raise ValueError("Messages cannot be retrieved individually from trash. They are part of conversations.")
                query = query.eq("item_type", item_type)

            # Order by deleted_at descending (most recent first)
            query = query.order("deleted_at", desc=True)

            # Apply pagination
            query = query.range(offset, offset + limit - 1)

            result = query.execute()

            # Get total count
            count_query = client.table("deleted_items_view").select("id", count="exact")
            count_query = count_query.neq("item_type", "message")  # Exclude messages from count too
            if item_type:
                if item_type != "message":
                    count_query = count_query.eq("item_type", item_type)
            count_result = count_query.execute()

            return {
                "items": result.data if result.data else [],
                "total": count_result.count if hasattr(count_result, 'count') else 0,
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            logger.error(f"Error getting deleted items: {e}")
            raise


    @staticmethod
    async def cleanup_old_deleted_items() -> Dict[str, Any]:
        """
        Permanently delete items that have been soft-deleted for 30+ days

        Returns:
            Dict with count of items deleted
        """
        try:
            client = get_supabase_client()

            # Call the database function for cleanup
            result = client.rpc('cleanup_old_deleted_items').execute()

            deleted_count = result.data if result.data else 0

            logger.info(f"Cleaned up {deleted_count} old deleted items")

            return {
                "success": True,
                "message": f"Cleaned up {deleted_count} items",
                "deleted_count": deleted_count
            }

        except Exception as e:
            logger.error(f"Error cleaning up old deleted items: {e}")
            raise


    @staticmethod
    async def update_conversation(
        conversation_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update conversation metadata

        Args:
            conversation_id: UUID of conversation to update
            user_id: UUID of user performing update
            updates: Dict of fields to update

        Returns:
            Updated conversation data
        """
        try:
            client = get_supabase_client()

            # Add updated_by field
            updates["updated_by"] = str(user_id)
            updates["updated_at"] = datetime.utcnow().isoformat()

            result = client.table("conversations").update(updates).eq(
                "id", str(conversation_id)
            ).execute()

            return {
                "success": True,
                "message": "Conversation updated successfully",
                "conversation": result.data[0] if result.data else None
            }

        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {e}")
            raise


    @staticmethod
    async def update_message(
        message_id: UUID,
        user_id: UUID,
        content: str
    ) -> Dict[str, Any]:
        """
        Update message content

        Args:
            message_id: UUID of message to update
            user_id: UUID of user performing update
            content: New message content

        Returns:
            Updated message data
        """
        try:
            client = get_supabase_client()

            result = client.table("messages").update({
                "content": content,
                "updated_by": str(user_id),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", str(message_id)).execute()

            return {
                "success": True,
                "message": "Message updated successfully",
                "message": result.data[0] if result.data else None
            }

        except Exception as e:
            logger.error(f"Error updating message {message_id}: {e}")
            raise


    @staticmethod
    async def update_feedback(
        feedback_id: UUID,
        user_id: UUID,
        rating: Optional[int] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update feedback

        Args:
            feedback_id: UUID of feedback to update
            user_id: UUID of user performing update
            rating: New rating (0 or 1)
            comment: New comment

        Returns:
            Updated feedback data
        """
        try:
            client = get_supabase_client()

            updates = {
                "updated_by": str(user_id),
                "updated_at": datetime.utcnow().isoformat()
            }

            if rating is not None:
                updates["rating"] = rating
            if comment is not None:
                updates["comment"] = comment

            result = client.table("feedback").update(updates).eq(
                "id", str(feedback_id)
            ).execute()

            return {
                "success": True,
                "message": "Feedback updated successfully",
                "feedback": result.data[0] if result.data else None
            }

        except Exception as e:
            logger.error(f"Error updating feedback {feedback_id}: {e}")
            raise
