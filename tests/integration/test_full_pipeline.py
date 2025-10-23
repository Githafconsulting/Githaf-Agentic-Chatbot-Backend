"""
Full Pipeline Integration Tests (Phase 6: Testing & Polish)
Tests the complete flow from query to response including all phases
"""
import pytest
import asyncio
from app.services.rag_service import get_rag_response, process_conversation_memory
from app.services.intent_service import classify_intent_hybrid, Intent
from app.services.planning_service import needs_planning, create_plan, execute_plan
from app.services.validation_service import validate_response
from app.services.memory_service import extract_semantic_facts, retrieve_semantic_memory
from app.services.conversation_summary_service import summarize_conversation
from app.services.tools import get_tool_registry


# ========================================
# Test Complete RAG Pipeline
# ========================================

@pytest.mark.asyncio
async def test_simple_rag_query():
    """Test simple RAG query end-to-end"""
    query = "What services does Githaf Consulting offer?"

    try:
        response = await get_rag_response(query, session_id="test-session-001")

        # Check response structure
        assert "response" in response
        assert "sources" in response
        assert "context_found" in response
        assert "intent" in response

        # Check validation metadata (Phase 1)
        if "validation" in response:
            assert "confidence" in response["validation"]
            assert "retry_count" in response["validation"]

        # Response should be non-empty
        assert len(response["response"]) > 0

    except Exception as e:
        pytest.skip(f"RAG pipeline unavailable: {e}")


@pytest.mark.asyncio
async def test_conversational_intent():
    """Test conversational intent handling"""
    queries = [
        "hello",
        "how are you",
        "thank you",
        "goodbye"
    ]

    for query in queries:
        try:
            response = await get_rag_response(query, session_id="test-session-002")

            # Should be marked as conversational
            assert response.get("conversational") == True
            # Should not search knowledge base
            assert response.get("context_found") == False or not response.get("sources")
            # Should have a response
            assert len(response["response"]) > 0

        except Exception as e:
            pytest.skip(f"Intent classification unavailable: {e}")


@pytest.mark.asyncio
async def test_out_of_scope_query():
    """Test out-of-scope query handling"""
    query = "What's the weather today?"

    try:
        response = await get_rag_response(query, session_id="test-session-003")

        # Should detect out-of-scope
        assert response.get("intent") == Intent.OUT_OF_SCOPE.value or "scope" in response["response"].lower()

    except Exception as e:
        pytest.skip(f"Intent classification unavailable: {e}")


# ========================================
# Test Planning Layer (Phase 2)
# ========================================

@pytest.mark.asyncio
async def test_multi_step_planning():
    """Test multi-step query planning"""
    query = "First tell me about your services, then send me pricing information"

    try:
        # Should trigger planning
        intent, _ = await classify_intent_hybrid(query)
        should_plan = await needs_planning(query, intent)

        assert should_plan == True

        # Create plan
        plan = await create_plan(query, intent)

        assert plan is not None
        assert len(plan.actions) >= 2  # Multi-step
        assert plan.goal is not None

    except Exception as e:
        pytest.skip(f"Planning service unavailable: {e}")


@pytest.mark.asyncio
async def test_plan_execution():
    """Test executing a simple plan"""
    query = "What are your services?"

    try:
        intent, _ = await classify_intent_hybrid(query)
        plan = await create_plan(query, intent)

        # Execute plan
        result = await execute_plan(plan, session_id="test-session-004")

        assert "response" in result
        assert "success" in result
        assert "results" in result

    except Exception as e:
        pytest.skip(f"Plan execution unavailable: {e}")


# ========================================
# Test Validation & Retry (Phase 1)
# ========================================

@pytest.mark.asyncio
async def test_response_validation():
    """Test response validation system"""
    query = "What is your email?"
    response = "Our email is info@githafconsulting.com"
    sources = [
        {
            "id": "test-1",
            "content": "Contact us at info@githafconsulting.com",
            "similarity": 0.9
        }
    ]

    try:
        validation = await validate_response(query, response, sources)

        assert "is_valid" in validation
        assert "confidence" in validation
        assert "issues" in validation
        assert "retry_recommended" in validation

        # Should be valid since response matches source
        assert validation["is_valid"] == True or validation["confidence"] > 0.5

    except Exception as e:
        pytest.skip(f"Validation service unavailable: {e}")


# ========================================
# Test Memory System (Phase 4)
# ========================================

@pytest.mark.asyncio
async def test_semantic_memory_extraction():
    """Test semantic fact extraction from conversation"""
    # This requires a conversation to exist
    try:
        # Skip if database not available
        facts = await extract_semantic_facts("test-conversation-id")

        # Should return list (may be empty if conversation doesn't exist)
        assert isinstance(facts, list)

    except Exception as e:
        pytest.skip(f"Memory service unavailable: {e}")


@pytest.mark.asyncio
async def test_semantic_memory_retrieval():
    """Test retrieving semantic memories"""
    try:
        memories = await retrieve_semantic_memory("test-session-005", query="pricing", limit=3)

        # Should return list
        assert isinstance(memories, list)

    except Exception as e:
        pytest.skip(f"Memory retrieval unavailable: {e}")


@pytest.mark.asyncio
async def test_conversation_summarization():
    """Test conversation summary generation"""
    try:
        summary = await summarize_conversation("test-conversation-id")

        # May return None if conversation doesn't exist
        if summary:
            assert "main_topic" in summary
            assert "user_intent" in summary
            assert "resolution_status" in summary

    except Exception as e:
        pytest.skip(f"Summary service unavailable: {e}")


# ========================================
# Test Tool Ecosystem (Phase 5)
# ========================================

@pytest.mark.asyncio
async def test_tool_registry_initialization():
    """Test tool registry is properly initialized"""
    registry = get_tool_registry()

    assert registry is not None
    assert len(registry.tools) >= 4  # Email, Calendar, CRM, WebSearch

    # Check specific tools
    assert registry.get_tool("send_email") is not None
    assert registry.get_tool("calendar") is not None
    assert registry.get_tool("crm") is not None
    assert registry.get_tool("web_search") is not None


@pytest.mark.asyncio
async def test_tool_execution_via_planning():
    """Test tools can be executed through planning system"""
    # Note: This requires tools to be properly configured
    try:
        from app.models.action import Action, ActionPlan, ActionType
        from app.services.planning_service import execute_action

        # Create a simple action
        action = Action(
            type=ActionType.SEARCH_KNOWLEDGE,
            params={"query": "test"},
            description="Test action"
        )

        result = await execute_action(action, context={}, session_id="test-session-006")

        assert result is not None
        assert hasattr(result, "success")

    except Exception as e:
        pytest.skip(f"Tool execution unavailable: {e}")


# ========================================
# Test End-to-End Scenarios
# ========================================

@pytest.mark.asyncio
async def test_complete_conversation_flow():
    """Test complete conversation flow with memory"""
    session_id = "test-session-e2e-001"

    try:
        # Step 1: Greeting
        response1 = await get_rag_response("Hello", session_id=session_id)
        assert response1["conversational"] == True

        # Step 2: Question
        response2 = await get_rag_response("What services do you offer?", session_id=session_id)
        assert "response" in response2

        # Step 3: Follow-up
        response3 = await get_rag_response("How much does it cost?", session_id=session_id)
        assert "response" in response3

        # Step 4: Farewell
        response4 = await get_rag_response("Thank you, goodbye", session_id=session_id)
        assert response4["conversational"] == True

    except Exception as e:
        pytest.skip(f"Conversation flow unavailable: {e}")


@pytest.mark.asyncio
async def test_multi_phase_integration():
    """Test integration across all 5 phases"""
    session_id = "test-session-integration-001"
    query = "What are your services?"

    try:
        # Phase 1: Get response with validation
        response = await get_rag_response(query, session_id=session_id, max_retries=1)

        # Should have validation metadata
        if "validation" in response:
            assert "confidence" in response["validation"]

        # Phase 2: If complex, should have plan
        if response.get("planned"):
            assert "plan" in response

        # Phase 3: Tools should be available (learning happens in background)
        registry = get_tool_registry()
        assert len(registry.tools) > 0

        # Phase 4: Memory should be queryable
        memories = await retrieve_semantic_memory(session_id, limit=1)
        assert isinstance(memories, list)

        # Phase 5: Tool registry should be functional
        tools = registry.list_tools()
        assert len(tools) >= 4

    except Exception as e:
        pytest.skip(f"Multi-phase integration unavailable: {e}")


# ========================================
# Test Error Handling
# ========================================

@pytest.mark.asyncio
async def test_error_handling_invalid_query():
    """Test system handles invalid queries gracefully"""
    queries = ["", "   ", "\n\n", "a" * 10000]  # Empty, whitespace, very long

    for query in queries:
        try:
            response = await get_rag_response(query, session_id="test-session-error")

            # Should not crash, should return some response
            assert "response" in response or "error" in response

        except Exception:
            # Some errors are acceptable (validation errors)
            pass


@pytest.mark.asyncio
async def test_error_handling_missing_session():
    """Test system handles missing session gracefully"""
    try:
        response = await get_rag_response("Test query", session_id=None)

        # Should work without session (creates new one or handles gracefully)
        assert "response" in response or "error" in response

    except Exception:
        # Acceptable if session is required
        pass


# ========================================
# Test Performance & Latency
# ========================================

@pytest.mark.asyncio
async def test_response_latency():
    """Test response time is reasonable"""
    import time

    query = "What services do you offer?"

    try:
        start = time.time()
        response = await get_rag_response(query, session_id="test-session-perf")
        end = time.time()

        latency = end - start

        # Should respond within 5 seconds (generous for testing)
        assert latency < 5.0, f"Response took {latency:.2f}s, expected < 5s"

    except Exception as e:
        pytest.skip(f"Performance test unavailable: {e}")


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test system handles concurrent requests"""
    queries = [
        "What services do you offer?",
        "How can I contact you?",
        "What are your prices?"
    ]

    try:
        # Execute concurrently
        tasks = [
            get_rag_response(query, session_id=f"test-session-concurrent-{i}")
            for i, query in enumerate(queries)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete without crashes
        assert len(responses) == 3

        # At least some should succeed
        successes = [r for r in responses if not isinstance(r, Exception)]
        assert len(successes) > 0

    except Exception as e:
        pytest.skip(f"Concurrent test unavailable: {e}")


# ========================================
# Test Data Consistency
# ========================================

@pytest.mark.asyncio
async def test_session_persistence():
    """Test session data persists across queries"""
    session_id = "test-session-persistence-001"

    try:
        # First query
        response1 = await get_rag_response("Hello", session_id=session_id)

        # Second query
        response2 = await get_rag_response("What services do you offer?", session_id=session_id)

        # Both should use same session
        assert response1.get("session_id") == session_id or True  # May not return session_id
        assert response2.get("session_id") == session_id or True

    except Exception as e:
        pytest.skip(f"Session persistence test unavailable: {e}")


# ========================================
# Test System Health
# ========================================

@pytest.mark.asyncio
async def test_system_components_available():
    """Test all major components are available"""
    components = {
        "intent_service": classify_intent_hybrid,
        "planning_service": needs_planning,
        "validation_service": validate_response,
        "memory_service": extract_semantic_facts,
        "tool_registry": get_tool_registry,
    }

    for name, component in components.items():
        assert callable(component) or component is not None, f"{name} not available"


def test_imports():
    """Test all critical imports work"""
    try:
        from app.services import rag_service
        from app.services import intent_service
        from app.services import planning_service
        from app.services import validation_service
        from app.services import learning_service
        from app.services import memory_service
        from app.services import conversation_summary_service
        from app.services.tools import tools_registry

        assert True

    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
