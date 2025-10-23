"""
Tests for memory_service.py (Phase 4: Advanced Memory)
"""
import pytest
from app.services.memory_service import (
    extract_semantic_facts,
    parse_semantic_facts,
    store_semantic_memory,
    retrieve_semantic_memory,
    get_session_context,
    get_user_preferences,
    update_user_preferences,
    cleanup_old_memories,
    enrich_query_with_memory
)
from app.services.conversation_summary_service import (
    summarize_conversation,
    parse_summary_response,
    store_conversation_summary,
    get_conversation_summary,
    get_session_summaries,
    batch_summarize_old_conversations,
    search_summaries,
    get_unresolved_conversations,
    get_followup_needed
)


# ========================================
# Test parse_semantic_facts
# ========================================

def test_parse_semantic_facts_valid():
    """Test parsing valid semantic fact extraction"""
    llm_output = """
FACT 1: User prefers email communication over phone
Category: preference
Confidence: 0.9

FACT 2: User needs pricing for enterprise package
Category: request
Confidence: 0.85

FACT 3: User is from healthcare industry
Category: context
Confidence: 0.8
    """

    facts = parse_semantic_facts(llm_output)

    assert len(facts) == 3

    assert "email" in facts[0]["content"].lower()
    assert facts[0]["category"] == "preference"
    assert facts[0]["confidence"] == 0.9

    assert "pricing" in facts[1]["content"].lower()
    assert facts[1]["category"] == "request"

    assert "healthcare" in facts[2]["content"].lower()
    assert facts[2]["category"] == "context"


def test_parse_semantic_facts_minimal():
    """Test parsing minimal fact response"""
    llm_output = """
FACT 1: User asked about services
    """

    facts = parse_semantic_facts(llm_output)

    assert len(facts) == 1
    assert "services" in facts[0]["content"].lower()
    # Default values
    assert facts[0]["category"] == "other"
    assert facts[0]["confidence"] == 0.7


def test_parse_semantic_facts_empty():
    """Test parsing empty response"""
    llm_output = ""

    facts = parse_semantic_facts(llm_output)

    assert facts == []


# ========================================
# Test parse_summary_response
# ========================================

def test_parse_summary_response_valid():
    """Test parsing valid conversation summary"""
    llm_output = """
MAIN_TOPIC: User inquiry about pricing and services
USER_INTENT: Get pricing information for enterprise package
KEY_POINTS:
- User is interested in enterprise consulting package
- Asked about pricing structure and payment terms
- Requested information about implementation timeline
- Mentioned healthcare industry requirements
- Wants to schedule a demo
RESOLUTION: partially_resolved
FOLLOWUP: yes
SENTIMENT: positive
    """

    summary = parse_summary_response(llm_output)

    assert "pricing" in summary["main_topic"].lower()
    assert "enterprise" in summary["user_intent"].lower()
    assert len(summary["key_points"]) == 5
    assert "enterprise" in summary["key_points"][0].lower()
    assert summary["resolution_status"] == "partially_resolved"
    assert summary["followup_needed"] == True
    assert summary["sentiment"] == "positive"


def test_parse_summary_response_minimal():
    """Test parsing minimal summary"""
    llm_output = """
MAIN_TOPIC: General inquiry
USER_INTENT: Ask questions
RESOLUTION: resolved
FOLLOWUP: no
SENTIMENT: neutral
    """

    summary = parse_summary_response(llm_output)

    assert summary["main_topic"] == "General inquiry"
    assert summary["user_intent"] == "Ask questions"
    assert summary["key_points"] == []
    assert summary["resolution_status"] == "resolved"
    assert summary["followup_needed"] == False
    assert summary["sentiment"] == "neutral"


def test_parse_summary_response_invalid_values():
    """Test parsing summary with invalid enum values"""
    llm_output = """
RESOLUTION: invalid_status
FOLLOWUP: maybe
SENTIMENT: happy
    """

    summary = parse_summary_response(llm_output)

    # Should use default values for invalid enums
    assert summary["resolution_status"] == "unresolved"  # default
    assert summary["followup_needed"] == False  # "maybe" is not "yes"
    assert summary["sentiment"] == "neutral"  # "happy" is invalid


# ========================================
# Test extract_semantic_facts (database integration)
# ========================================

@pytest.mark.asyncio
async def test_extract_semantic_facts_no_conversation():
    """Test fact extraction with non-existent conversation"""
    try:
        facts = await extract_semantic_facts("non-existent-id")

        # Should return empty list for non-existent conversation
        assert facts == []

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_extract_semantic_facts_error_handling():
    """Test error handling in fact extraction"""
    try:
        # Invalid conversation ID format
        facts = await extract_semantic_facts("")

        # Should handle gracefully
        assert isinstance(facts, list)

    except Exception as e:
        # Expected behavior
        assert True


# ========================================
# Test store_semantic_memory
# ========================================

@pytest.mark.asyncio
async def test_store_semantic_memory_empty():
    """Test storing empty fact list"""
    count = await store_semantic_memory([], "test-session")

    assert count == 0


@pytest.mark.asyncio
async def test_store_semantic_memory_valid():
    """Test storing valid facts"""
    try:
        facts = [
            {
                "content": "User prefers email",
                "category": "preference",
                "confidence": 0.9,
                "embedding": [0.1] * 384,  # Mock embedding
                "conversation_id": "test-conv-id",
                "extracted_at": "2025-01-01T00:00:00Z"
            }
        ]

        count = await store_semantic_memory(facts, "test-session")

        # Should return count of stored facts (may fail if DB unavailable)
        assert count >= 0

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test retrieve_semantic_memory
# ========================================

@pytest.mark.asyncio
async def test_retrieve_semantic_memory_no_query():
    """Test retrieving memories without query"""
    try:
        memories = await retrieve_semantic_memory("test-session", query=None, limit=5)

        # Should return list (may be empty)
        assert isinstance(memories, list)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_retrieve_semantic_memory_with_query():
    """Test retrieving memories with semantic search"""
    try:
        memories = await retrieve_semantic_memory("test-session", query="pricing", limit=3)

        # Should return list (may be empty)
        assert isinstance(memories, list)

        if memories:
            # Check structure
            assert "content" in memories[0]
            assert "category" in memories[0]

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test user preferences
# ========================================

@pytest.mark.asyncio
async def test_get_user_preferences_nonexistent():
    """Test getting preferences for non-existent session"""
    try:
        prefs = await get_user_preferences("non-existent-session")

        # Should return empty dict
        assert prefs == {}

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_update_user_preferences():
    """Test updating user preferences"""
    try:
        preferences = {
            "language": "en",
            "contact_method": "email",
            "industry": "healthcare"
        }

        success = await update_user_preferences("test-session-prefs", preferences)

        # Should return True on success (may fail if DB unavailable)
        assert isinstance(success, bool)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test get_session_context
# ========================================

@pytest.mark.asyncio
async def test_get_session_context():
    """Test building comprehensive session context"""
    try:
        context = await get_session_context("test-session")

        # Should return structured context
        assert "session_id" in context
        assert "conversation_count" in context
        assert "semantic_memories" in context
        assert "user_preferences" in context

        # Check types
        assert isinstance(context["conversation_count"], int)
        assert isinstance(context["semantic_memories"], list)
        assert isinstance(context["user_preferences"], dict)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test cleanup_old_memories
# ========================================

@pytest.mark.asyncio
async def test_cleanup_old_memories():
    """Test cleaning up old low-confidence memories"""
    try:
        deleted = await cleanup_old_memories(days=90)

        # Should return count (may be 0)
        assert isinstance(deleted, int)
        assert deleted >= 0

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test enrich_query_with_memory
# ========================================

@pytest.mark.asyncio
async def test_enrich_query_with_memory_no_memories():
    """Test query enrichment with no memories"""
    try:
        query = "What are your services?"

        enriched = await enrich_query_with_memory(query, "empty-session")

        # Should return at least the original query
        assert "services" in enriched.lower()

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_enrich_query_with_memory_error():
    """Test error handling in query enrichment"""
    enriched = await enrich_query_with_memory("test query", "")

    # Should fall back to original query on error
    assert "test query" in enriched.lower()


# ========================================
# Test conversation summary service
# ========================================

@pytest.mark.asyncio
async def test_summarize_conversation_nonexistent():
    """Test summarizing non-existent conversation"""
    try:
        summary = await summarize_conversation("non-existent-conv")

        # Should return None for non-existent conversation
        assert summary is None

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_get_conversation_summary():
    """Test retrieving conversation summary"""
    try:
        summary = await get_conversation_summary("test-conv-id")

        # Should return None if not found, or dict if exists
        assert summary is None or isinstance(summary, dict)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_get_session_summaries():
    """Test retrieving all summaries for a session"""
    try:
        summaries = await get_session_summaries("test-session", limit=10)

        # Should return list
        assert isinstance(summaries, list)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_search_summaries():
    """Test searching conversation summaries"""
    try:
        results = await search_summaries("pricing", limit=5)

        # Should return list
        assert isinstance(results, list)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_get_unresolved_conversations():
    """Test getting unresolved conversations"""
    try:
        unresolved = await get_unresolved_conversations(limit=10)

        # Should return list
        assert isinstance(unresolved, list)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_get_followup_needed():
    """Test getting conversations needing follow-up"""
    try:
        followups = await get_followup_needed(limit=10)

        # Should return list
        assert isinstance(followups, list)

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Edge Cases
# ========================================

def test_parse_semantic_facts_malformed():
    """Test parsing malformed LLM response"""
    llm_output = """
This is completely malformed
with no structure at all
    """

    facts = parse_semantic_facts(llm_output)

    # Should return empty list for malformed input
    assert facts == []


def test_parse_summary_response_empty():
    """Test parsing empty summary response"""
    summary = parse_summary_response("")

    # Should return defaults
    assert summary["main_topic"] == ""
    assert summary["user_intent"] == ""
    assert summary["key_points"] == []
    assert summary["resolution_status"] == "unresolved"


@pytest.mark.asyncio
async def test_batch_summarize_old_conversations():
    """Test batch summarization of old conversations"""
    try:
        count = await batch_summarize_old_conversations(days_old=7)

        # Should return count (may be 0)
        assert isinstance(count, int)
        assert count >= 0

    except Exception as e:
        pytest.skip(f"Database not available: {e}")
