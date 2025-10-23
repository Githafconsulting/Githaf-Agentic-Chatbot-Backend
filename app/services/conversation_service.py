"""
Conversation service for session and context management
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid
from app.core.database import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_conversation(
    session_id: str,
    ip_address: Optional[str] = None,
    country_code: Optional[str] = None,
    country_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new conversation

    Args:
        session_id: Session identifier
        ip_address: Client IP address (optional)
        country_code: ISO country code (optional)
        country_name: Country name (optional)

    Returns:
        Dict: Created conversation record
    """
    try:
        client = get_supabase_client()

        data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_message_at": datetime.utcnow().isoformat()
        }

        # Add IP tracking data if provided
        if ip_address:
            data["ip_address"] = ip_address
        if country_code:
            data["country_code"] = country_code
        if country_name:
            data["country_name"] = country_name

        response = client.table("conversations").insert(data).execute()

        # logger.debug(f"Created new conversation: {session_id}")

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise


async def get_or_create_conversation(
    session_id: str,
    ip_address: Optional[str] = None,
    country_code: Optional[str] = None,
    country_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get existing conversation or create new one

    Args:
        session_id: Session identifier
        ip_address: Client IP address (optional, anonymized)
        country_code: ISO country code (optional)
        country_name: Country name (optional)

    Returns:
        Dict: Conversation record
    """
    try:
        client = get_supabase_client()

        # Try to find existing conversation
        response = client.table("conversations").select("*").eq("session_id", session_id).execute()

        if response.data and len(response.data) > 0:
            # logger.debug(f"Found existing conversation: {session_id}")
            return response.data[0]

        # Create new conversation with IP tracking data
        return await create_conversation(
            session_id=session_id,
            ip_address=ip_address,
            country_code=country_code,
            country_name=country_name
        )

    except Exception as e:
        logger.error(f"Error getting or creating conversation: {e}")
        raise


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    context_used: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Save a message to the database

    Args:
        conversation_id: Conversation ID
        role: Message role (user or assistant)
        content: Message content
        context_used: Optional context/sources used

    Returns:
        Dict: Created message record
    """
    try:
        client = get_supabase_client()

        data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "context_used": context_used,
            "created_at": datetime.utcnow().isoformat()
        }

        response = client.table("messages").insert(data).execute()

        # Update conversation last_message_at
        client.table("conversations").update({
            "last_message_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).execute()

        # logger.debug(f"Saved {role} message to conversation {conversation_id}")

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error saving message: {e}")
        raise


async def get_conversation_history(
    session_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get conversation history for a session

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return

    Returns:
        List[Dict]: List of messages
    """
    try:
        client = get_supabase_client()

        # Get conversation
        conv_response = client.table("conversations").select("id").eq("session_id", session_id).execute()

        if not conv_response.data or len(conv_response.data) == 0:
            return []

        conversation_id = conv_response.data[0]["id"]

        # Get messages
        messages_response = client.table("messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at", desc=False).limit(limit).execute()

        messages = messages_response.data if messages_response.data else []

        # logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")

        return messages

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []


async def format_history_for_llm(messages: List[Dict[str, Any]]) -> str:
    """
    Format conversation history for LLM context

    Args:
        messages: List of message records

    Returns:
        str: Formatted conversation history
    """
    if not messages:
        return "No previous conversation."

    formatted = []
    for msg in messages:
        role = msg.get("role", "").capitalize()
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


async def get_all_conversations(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Get all conversations (for admin dashboard)

    Note: Only returns active (non-deleted) conversations.
    Soft-deleted conversations are excluded from the list.
    All conversations are returned (no pagination) for scrollable display.

    Args:
        limit: Ignored (kept for API compatibility)
        offset: Ignored (kept for API compatibility)

    Returns:
        Dict with 'conversations' list and 'total' count
    """
    try:
        client = get_supabase_client()

        # Get all conversations
        all_response = client.table("conversations").select(
            "*"
        ).order("last_message_at", desc=True).execute()

        all_conversations = all_response.data if all_response.data else []

        # Filter out soft-deleted conversations in Python (where deleted_at is not None)
        active_conversations = [
            conv for conv in all_conversations
            if conv.get("deleted_at") is None
        ]

        return {
            "conversations": active_conversations,
            "total": len(active_conversations)
        }

    except Exception as e:
        logger.error(f"Error getting all conversations: {e}")
        logger.exception(e)  # Full stack trace
        return {
            "conversations": [],
            "total": 0
        }


async def get_conversation_detail(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed conversation with messages

    Note: Only returns active (non-deleted) conversations.
    Soft-deleted conversations return None (404 to client).

    Args:
        conversation_id: Conversation ID

    Returns:
        Dict: Conversation with messages, or None if not found or deleted
    """
    try:
        client = get_supabase_client()

        # Get conversation - exclude soft-deleted
        conv_response = client.table("conversations").select("*").eq(
            "id", conversation_id
        ).is_("deleted_at", "null").execute()

        if not conv_response.data:
            return None

        conversation = conv_response.data[0]

        # Get messages - exclude soft-deleted messages
        messages_response = client.table("messages").select("*").eq(
            "conversation_id", conversation_id
        ).is_("deleted_at", "null").order("created_at", desc=False).execute()

        conversation["messages"] = messages_response.data if messages_response.data else []

        return conversation

    except Exception as e:
        logger.error(f"Error getting conversation detail: {e}")
        return None


async def end_conversation(session_id: str) -> bool:
    """
    Mark a conversation as ended (when user closes chatbot window)

    Args:
        session_id: Session identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_supabase_client()

        # Update conversation with ended_at timestamp
        response = client.table("conversations").update({
            "ended_at": datetime.utcnow().isoformat()
        }).eq("session_id", session_id).execute()

        if response.data:
            logger.debug(f"Conversation ended: {session_id}")
            return True

        return False

    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        return False
