"""
Memory Service (Phase 4: Advanced Memory)
Long-term semantic memory and conversation context storage
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.core.database import get_supabase_client
from app.services.llm_service import generate_response
from app.services.embedding_service import get_embedding
from app.utils.logger import get_logger
import json

logger = get_logger(__name__)


async def extract_semantic_facts(conversation_id: str) -> List[Dict]:
    """
    Extract important facts from a conversation using LLM

    Args:
        conversation_id: ID of the conversation to analyze

    Returns:
        List of extracted facts with metadata
    """
    logger.info(f"Extracting semantic facts from conversation {conversation_id}")

    client = get_supabase_client()

    try:
        # Get conversation messages
        messages_response = client.table("messages").select(
            "id, role, content, created_at"
        ).eq("conversation_id", conversation_id).order(
            "created_at", desc=False
        ).execute()

        messages = messages_response.data or []

        if not messages:
            logger.warning(f"No messages found for conversation {conversation_id}")
            return []

        # Build conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])

        # Use LLM to extract facts
        extraction_prompt = f"""You are a semantic fact extractor. Analyze this customer service conversation and extract important factual information.

Conversation:
{conversation_text}

Extract facts such as:
- User preferences (e.g., "User prefers email communication")
- Specific requests (e.g., "User needs pricing for enterprise package")
- Business context (e.g., "User is from healthcare industry")
- Follow-up needs (e.g., "User wants to schedule a demo")
- Problems mentioned (e.g., "User experiencing integration issues")

Respond in this EXACT format:

FACT 1: [factual statement]
Category: [preference|request|context|followup|problem|other]
Confidence: [0.0-1.0]

FACT 2: [factual statement]
Category: [category]
Confidence: [0.0-1.0]

(List all relevant facts, minimum 0, maximum 10)

Facts:"""

        llm_response = await generate_response(extraction_prompt, max_tokens=600, temperature=0.3)

        # Parse facts
        facts = parse_semantic_facts(llm_response)

        # Generate embeddings for each fact
        facts_with_embeddings = []
        for fact in facts:
            try:
                embedding = await get_embedding(fact["content"])
                facts_with_embeddings.append({
                    **fact,
                    "embedding": embedding,
                    "conversation_id": conversation_id,
                    "extracted_at": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to generate embedding for fact: {e}")

        logger.info(f"Extracted {len(facts_with_embeddings)} facts from conversation")
        return facts_with_embeddings

    except Exception as e:
        logger.error(f"Error extracting semantic facts: {e}")
        return []


def parse_semantic_facts(text: str) -> List[Dict]:
    """Parse LLM fact extraction response"""
    facts = []
    lines = text.strip().split("\n")

    current_fact = None

    for line in lines:
        line = line.strip()

        if line.startswith("FACT"):
            if current_fact and current_fact.get("content"):
                facts.append(current_fact)

            # Extract fact content
            fact_content = line.split(":", 1)[1].strip() if ":" in line else ""
            current_fact = {
                "content": fact_content,
                "category": "other",
                "confidence": 0.7
            }

        elif line.startswith("Category:") and current_fact:
            category = line.split(":", 1)[1].strip().lower()
            if category in ["preference", "request", "context", "followup", "problem", "other"]:
                current_fact["category"] = category

        elif line.startswith("Confidence:") and current_fact:
            try:
                confidence_str = line.split(":", 1)[1].strip()
                current_fact["confidence"] = float(confidence_str)
            except:
                pass

    # Add last fact
    if current_fact and current_fact.get("content"):
        facts.append(current_fact)

    return facts


async def store_semantic_memory(facts: List[Dict], session_id: str) -> int:
    """
    Store semantic facts in long-term memory

    Args:
        facts: List of facts with embeddings
        session_id: Session identifier

    Returns:
        Number of facts stored
    """
    if not facts:
        return 0

    logger.info(f"Storing {len(facts)} semantic facts for session {session_id}")

    client = get_supabase_client()

    try:
        # Store in semantic_memory table
        for fact in facts:
            # Prepare data
            memory_data = {
                "session_id": session_id,
                "conversation_id": fact.get("conversation_id"),
                "content": fact["content"],
                "category": fact.get("category", "other"),
                "confidence": fact.get("confidence", 0.7),
                "embedding": fact["embedding"],
                "metadata": {
                    "extracted_at": fact.get("extracted_at"),
                    "source": "llm_extraction"
                }
            }

            client.table("semantic_memory").insert(memory_data).execute()

        logger.info(f"Successfully stored {len(facts)} facts")
        return len(facts)

    except Exception as e:
        logger.error(f"Error storing semantic memory: {e}")
        return 0


async def retrieve_semantic_memory(
    session_id: str,
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Retrieve relevant semantic memories

    Args:
        session_id: Session identifier
        query: Optional query for semantic search
        category: Optional category filter
        limit: Maximum number of memories to retrieve

    Returns:
        List of relevant memories
    """
    logger.info(f"Retrieving semantic memory for session {session_id}")

    client = get_supabase_client()

    try:
        if query:
            # Semantic search using embedding
            query_embedding = await get_embedding(query)

            # Use RPC function for vector search
            response = client.rpc(
                "match_semantic_memory",
                {
                    "query_embedding": query_embedding,
                    "session_filter": session_id,
                    "match_threshold": 0.6,
                    "match_count": limit
                }
            ).execute()

            memories = response.data or []

        else:
            # Simple retrieval by session and category
            query_builder = client.table("semantic_memory").select(
                "id, content, category, confidence, created_at, metadata"
            ).eq("session_id", session_id)

            if category:
                query_builder = query_builder.eq("category", category)

            response = query_builder.order("created_at", desc=True).limit(limit).execute()

            memories = response.data or []

        logger.info(f"Retrieved {len(memories)} semantic memories")
        return memories

    except Exception as e:
        logger.error(f"Error retrieving semantic memory: {e}")
        return []


async def get_session_context(session_id: str) -> Dict[str, Any]:
    """
    Get full session context including memories, preferences, and recent conversations

    Args:
        session_id: Session identifier

    Returns:
        Comprehensive session context
    """
    logger.info(f"Building session context for {session_id}")

    client = get_supabase_client()

    try:
        # Get recent semantic memories
        memories = await retrieve_semantic_memory(session_id, limit=10)

        # Get user preferences (if available)
        preferences = await get_user_preferences(session_id)

        # Get conversation count
        conversations_response = client.table("conversations").select(
            "id", count="exact"
        ).eq("session_id", session_id).execute()

        conversation_count = conversations_response.count or 0

        # Get recent conversations
        recent_convs = client.table("conversations").select(
            "id, created_at, last_message_at"
        ).eq("session_id", session_id).order(
            "created_at", desc=True
        ).limit(5).execute()

        context = {
            "session_id": session_id,
            "conversation_count": conversation_count,
            "semantic_memories": memories,
            "user_preferences": preferences,
            "recent_conversations": recent_convs.data or [],
            "context_loaded_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Session context built: {conversation_count} conversations, {len(memories)} memories")
        return context

    except Exception as e:
        logger.error(f"Error building session context: {e}")
        return {
            "session_id": session_id,
            "error": str(e)
        }


async def get_user_preferences(session_id: str) -> Dict[str, Any]:
    """
    Get user preferences for a session

    Args:
        session_id: Session identifier

    Returns:
        User preferences dictionary
    """
    client = get_supabase_client()

    try:
        response = client.table("user_preferences").select("*").eq(
            "session_id", session_id
        ).execute()

        if response.data:
            return response.data[0]
        else:
            return {}

    except Exception as e:
        logger.warning(f"Error retrieving user preferences: {e}")
        return {}


async def update_user_preferences(session_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Update or create user preferences

    Args:
        session_id: Session identifier
        preferences: Preference dictionary

    Returns:
        Success status
    """
    logger.info(f"Updating user preferences for session {session_id}")

    client = get_supabase_client()

    try:
        # Check if preferences exist
        existing = client.table("user_preferences").select("id").eq(
            "session_id", session_id
        ).execute()

        data = {
            "session_id": session_id,
            "preferences": preferences,
            "updated_at": datetime.utcnow().isoformat()
        }

        if existing.data:
            # Update existing
            client.table("user_preferences").update(data).eq(
                "session_id", session_id
            ).execute()
        else:
            # Insert new
            client.table("user_preferences").insert(data).execute()

        logger.info("User preferences updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        return False


async def cleanup_old_memories(days: int = 90) -> int:
    """
    Clean up semantic memories older than specified days

    Args:
        days: Age threshold in days

    Returns:
        Number of memories deleted
    """
    logger.info(f"Cleaning up semantic memories older than {days} days")

    client = get_supabase_client()
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    try:
        # Delete old memories with low confidence
        response = client.table("semantic_memory").delete().lt(
            "created_at", cutoff_date
        ).lt("confidence", 0.5).execute()

        deleted_count = len(response.data) if response.data else 0

        logger.info(f"Deleted {deleted_count} old low-confidence memories")
        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up memories: {e}")
        return 0


async def enrich_query_with_memory(query: str, session_id: str) -> str:
    """
    Enrich user query with relevant semantic memories

    Args:
        query: User query
        session_id: Session identifier

    Returns:
        Enriched query with context
    """
    logger.debug(f"Enriching query with memory for session {session_id}")

    try:
        # Retrieve relevant memories
        memories = await retrieve_semantic_memory(session_id, query=query, limit=3)

        if not memories:
            return query

        # Build context string
        memory_context = "\n".join([
            f"- {mem['content']} ({mem['category']})"
            for mem in memories
        ])

        enriched = f"""Query: {query}

Relevant context from previous interactions:
{memory_context}"""

        logger.debug("Query enriched with memory context")
        return enriched

    except Exception as e:
        logger.warning(f"Error enriching query with memory: {e}")
        return query
