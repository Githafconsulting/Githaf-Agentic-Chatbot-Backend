"""
Conversation Summary Service (Phase 4: Advanced Memory)
Automatic conversation summarization for long-term storage
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.services.llm_service import generate_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def summarize_conversation(conversation_id: str, force: bool = False) -> Optional[Dict]:
    """
    Generate summary for a conversation

    Args:
        conversation_id: ID of conversation to summarize
        force: Force regeneration even if summary exists

    Returns:
        Summary data or None
    """
    logger.info(f"Summarizing conversation {conversation_id}")

    client = get_supabase_client()

    try:
        # Check if summary already exists
        if not force:
            existing = client.table("conversation_summaries").select("*").eq(
                "conversation_id", conversation_id
            ).execute()

            if existing.data:
                logger.info("Summary already exists, returning cached version")
                return existing.data[0]

        # Get conversation messages
        messages_response = client.table("messages").select(
            "id, role, content, created_at"
        ).eq("conversation_id", conversation_id).order(
            "created_at", desc=False
        ).execute()

        messages = messages_response.data or []

        if not messages:
            logger.warning(f"No messages found for conversation {conversation_id}")
            return None

        # Don't summarize very short conversations
        if len(messages) < 4:
            logger.info("Conversation too short to summarize (< 4 messages)")
            return None

        # Build conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])

        # Use LLM to generate summary
        summary_prompt = f"""You are a conversation summarizer. Create a concise summary of this customer service conversation.

Conversation ({len(messages)} messages):
{conversation_text}

Create a structured summary with:

1. **Main Topic**: What was the conversation about? (1 sentence)
2. **User Intent**: What did the user want? (1 sentence)
3. **Key Points**: Important details discussed (3-5 bullet points)
4. **Resolution Status**: Was the query resolved? (resolved|partially_resolved|unresolved)
5. **Follow-up Needed**: Does this require follow-up? (yes|no)
6. **Sentiment**: Overall conversation tone (positive|neutral|negative)

Respond in this EXACT format:

MAIN_TOPIC: [topic]
USER_INTENT: [intent]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]
RESOLUTION: [status]
FOLLOWUP: [yes/no]
SENTIMENT: [sentiment]

Summary:"""

        llm_response = await generate_response(summary_prompt, max_tokens=400, temperature=0.3)

        # Parse summary
        summary_data = parse_summary_response(llm_response)

        # Add metadata
        summary_data.update({
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "first_message_at": messages[0]["created_at"],
            "last_message_at": messages[-1]["created_at"],
            "summarized_at": datetime.utcnow().isoformat()
        })

        # Store summary
        stored = await store_conversation_summary(summary_data)

        if stored:
            logger.info("Conversation summary generated and stored")
            return summary_data
        else:
            logger.warning("Failed to store summary")
            return summary_data

    except Exception as e:
        logger.error(f"Error summarizing conversation: {e}")
        return None


def parse_summary_response(text: str) -> Dict:
    """Parse LLM summary response into structured format"""
    lines = text.strip().split("\n")

    summary = {
        "main_topic": "",
        "user_intent": "",
        "key_points": [],
        "resolution_status": "unresolved",
        "followup_needed": False,
        "sentiment": "neutral"
    }

    current_section = None

    for line in lines:
        line = line.strip()

        if line.startswith("MAIN_TOPIC:"):
            summary["main_topic"] = line.split(":", 1)[1].strip()

        elif line.startswith("USER_INTENT:"):
            summary["user_intent"] = line.split(":", 1)[1].strip()

        elif line.startswith("KEY_POINTS:"):
            current_section = "key_points"

        elif line.startswith("RESOLUTION:"):
            resolution = line.split(":", 1)[1].strip().lower()
            if resolution in ["resolved", "partially_resolved", "unresolved"]:
                summary["resolution_status"] = resolution

        elif line.startswith("FOLLOWUP:"):
            followup = line.split(":", 1)[1].strip().lower()
            summary["followup_needed"] = followup == "yes"

        elif line.startswith("SENTIMENT:"):
            sentiment = line.split(":", 1)[1].strip().lower()
            if sentiment in ["positive", "neutral", "negative"]:
                summary["sentiment"] = sentiment

        elif current_section == "key_points" and (line.startswith("-") or line.startswith("•")):
            point = line[1:].strip()
            if point:
                summary["key_points"].append(point)

    return summary


async def store_conversation_summary(summary_data: Dict) -> bool:
    """
    Store conversation summary in database

    Args:
        summary_data: Summary dictionary

    Returns:
        Success status
    """
    logger.debug(f"Storing summary for conversation {summary_data.get('conversation_id')}")

    client = get_supabase_client()

    try:
        # Check if summary exists
        existing = client.table("conversation_summaries").select("id").eq(
            "conversation_id", summary_data["conversation_id"]
        ).execute()

        if existing.data:
            # Update existing
            client.table("conversation_summaries").update(summary_data).eq(
                "conversation_id", summary_data["conversation_id"]
            ).execute()
        else:
            # Insert new
            client.table("conversation_summaries").insert(summary_data).execute()

        return True

    except Exception as e:
        logger.error(f"Error storing conversation summary: {e}")
        return False


async def get_conversation_summary(conversation_id: str) -> Optional[Dict]:
    """
    Retrieve conversation summary

    Args:
        conversation_id: Conversation ID

    Returns:
        Summary data or None
    """
    client = get_supabase_client()

    try:
        response = client.table("conversation_summaries").select("*").eq(
            "conversation_id", conversation_id
        ).execute()

        if response.data:
            return response.data[0]
        else:
            return None

    except Exception as e:
        logger.error(f"Error retrieving conversation summary: {e}")
        return None


async def get_session_summaries(session_id: str, limit: int = 10) -> List[Dict]:
    """
    Get all conversation summaries for a session

    Args:
        session_id: Session identifier
        limit: Maximum number of summaries

    Returns:
        List of summaries
    """
    logger.info(f"Retrieving conversation summaries for session {session_id}")

    client = get_supabase_client()

    try:
        # Get conversations for session
        conversations_response = client.table("conversations").select(
            "id"
        ).eq("session_id", session_id).execute()

        conversation_ids = [conv["id"] for conv in conversations_response.data or []]

        if not conversation_ids:
            return []

        # Get summaries
        summaries_response = client.table("conversation_summaries").select(
            "*"
        ).in_("conversation_id", conversation_ids).order(
            "summarized_at", desc=True
        ).limit(limit).execute()

        return summaries_response.data or []

    except Exception as e:
        logger.error(f"Error retrieving session summaries: {e}")
        return []


async def batch_summarize_old_conversations(days_old: int = 7) -> int:
    """
    Batch summarize old conversations that don't have summaries

    Args:
        days_old: Only summarize conversations older than this many days

    Returns:
        Number of conversations summarized
    """
    logger.info(f"Batch summarizing conversations older than {days_old} days")

    client = get_supabase_client()
    cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()

    try:
        # Get old conversations without summaries
        conversations_response = client.table("conversations").select(
            "id, created_at"
        ).lt("created_at", cutoff_date).execute()

        conversations = conversations_response.data or []

        # Check which ones already have summaries
        if conversations:
            conv_ids = [conv["id"] for conv in conversations]
            summaries_response = client.table("conversation_summaries").select(
                "conversation_id"
            ).in_("conversation_id", conv_ids).execute()

            summarized_ids = {s["conversation_id"] for s in summaries_response.data or []}

            # Filter out conversations that already have summaries
            to_summarize = [conv for conv in conversations if conv["id"] not in summarized_ids]
        else:
            to_summarize = []

        logger.info(f"Found {len(to_summarize)} conversations to summarize")

        # Summarize each conversation
        summarized_count = 0
        for conv in to_summarize[:50]:  # Limit to 50 per batch to avoid timeouts
            try:
                summary = await summarize_conversation(conv["id"])
                if summary:
                    summarized_count += 1
            except Exception as e:
                logger.warning(f"Failed to summarize conversation {conv['id']}: {e}")

        logger.info(f"Batch summarization complete: {summarized_count} conversations")
        return summarized_count

    except Exception as e:
        logger.error(f"Error in batch summarization: {e}")
        return 0


async def search_summaries(query: str, limit: int = 10) -> List[Dict]:
    """
    Search conversation summaries by text

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching summaries
    """
    logger.info(f"Searching summaries for: {query}")

    client = get_supabase_client()

    try:
        # Simple text search on main_topic and user_intent
        # Note: This uses Supabase's text search. For production, consider full-text search
        response = client.table("conversation_summaries").select(
            "*"
        ).or_(
            f"main_topic.ilike.%{query}%,user_intent.ilike.%{query}%"
        ).limit(limit).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Error searching summaries: {e}")
        return []


async def get_unresolved_conversations(limit: int = 20) -> List[Dict]:
    """
    Get conversations marked as unresolved

    Args:
        limit: Maximum results

    Returns:
        List of unresolved conversation summaries
    """
    logger.info("Retrieving unresolved conversations")

    client = get_supabase_client()

    try:
        response = client.table("conversation_summaries").select(
            "*"
        ).eq("resolution_status", "unresolved").order(
            "summarized_at", desc=True
        ).limit(limit).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Error retrieving unresolved conversations: {e}")
        return []


async def get_followup_needed(limit: int = 20) -> List[Dict]:
    """
    Get conversations that need follow-up

    Args:
        limit: Maximum results

    Returns:
        List of conversation summaries needing follow-up
    """
    logger.info("Retrieving conversations needing follow-up")

    client = get_supabase_client()

    try:
        response = client.table("conversation_summaries").select(
            "*"
        ).eq("followup_needed", True).order(
            "summarized_at", desc=True
        ).limit(limit).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Error retrieving follow-up conversations: {e}")
        return []
