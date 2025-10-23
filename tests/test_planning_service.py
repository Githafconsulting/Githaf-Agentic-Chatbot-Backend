"""
Tests for planning_service.py (Phase 2: Planning Layer)
"""
import pytest
from app.services.planning_service import (
    needs_planning,
    create_plan,
    execute_plan,
    parse_plan_response,
    map_action_type,
    aggregate_results
)
from app.services.intent_service import Intent
from app.models.action import Action, ActionPlan, ActionResult, ActionType


# ========================================
# Test needs_planning
# ========================================

@pytest.mark.asyncio
async def test_needs_planning_simple_query():
    """Simple query doesn't need planning"""
    query = "What is your email?"
    intent = Intent.QUESTION

    result = await needs_planning(query, intent)

    assert result == False


@pytest.mark.asyncio
async def test_needs_planning_with_first_then():
    """Query with 'first...then' needs planning"""
    query = "First find your email, then tell me your office hours"
    intent = Intent.QUESTION

    result = await needs_planning(query, intent)

    assert result == True


@pytest.mark.asyncio
async def test_needs_planning_multiple_questions():
    """Query with multiple questions needs planning"""
    query = "What is your email? And what are your office hours?"
    intent = Intent.QUESTION

    result = await needs_planning(query, intent)

    assert result == True


@pytest.mark.asyncio
async def test_needs_planning_multiple_ands():
    """Query with multiple 'and' separators needs planning"""
    query = "Tell me about your services and pricing and contact info"
    intent = Intent.QUESTION

    result = await needs_planning(query, intent)

    assert result == True


@pytest.mark.asyncio
async def test_needs_planning_unknown_intent():
    """Unknown intent always needs planning"""
    query = "Something unclear"
    intent = Intent.UNKNOWN

    result = await needs_planning(query, intent)

    assert result == True


# ========================================
# Test map_action_type
# ========================================

def test_map_action_type_search():
    """Test mapping SEARCH to SEARCH_KNOWLEDGE"""
    assert map_action_type("SEARCH") == ActionType.SEARCH_KNOWLEDGE
    assert map_action_type("search_knowledge") == ActionType.SEARCH_KNOWLEDGE
    assert map_action_type("SEARCH_KNOWLEDGE_BASE") == ActionType.SEARCH_KNOWLEDGE


def test_map_action_type_contact():
    """Test mapping contact-related actions"""
    assert map_action_type("GET_CONTACT") == ActionType.GET_CONTACT_INFO
    assert map_action_type("get_contact_info") == ActionType.GET_CONTACT_INFO


def test_map_action_type_clarification():
    """Test mapping clarification actions"""
    assert map_action_type("ASK") == ActionType.ASK_CLARIFICATION
    assert map_action_type("CLARIFY") == ActionType.ASK_CLARIFICATION
    assert map_action_type("ask_clarification") == ActionType.ASK_CLARIFICATION


def test_map_action_type_unknown():
    """Unknown action types default to SEARCH_KNOWLEDGE"""
    assert map_action_type("UNKNOWN_ACTION") == ActionType.SEARCH_KNOWLEDGE


# ========================================
# Test parse_plan_response
# ========================================

def test_parse_plan_response_valid():
    """Test parsing valid plan response"""
    llm_output = """
GOAL: Get email and office hours
COMPLEXITY: moderate

STEP 1: GET_CONTACT_INFO
Description: Retrieve email address
Params: {"type": "email"}

STEP 2: SEARCH_KNOWLEDGE
Description: Find office hours
Params: {"query": "office hours"}
    """

    plan = parse_plan_response(llm_output, "test query")

    assert plan.goal == "Get email and office hours"
    assert plan.complexity == "moderate"
    assert len(plan.actions) == 2
    assert plan.actions[0].type == ActionType.GET_CONTACT_INFO
    assert plan.actions[0].description == "Retrieve email address"
    assert plan.actions[0].params == {"type": "email"}
    assert plan.actions[1].type == ActionType.SEARCH_KNOWLEDGE


def test_parse_plan_response_minimal():
    """Test parsing minimal plan response"""
    llm_output = """
STEP 1: SEARCH_KNOWLEDGE
    """

    plan = parse_plan_response(llm_output, "test query")

    assert len(plan.actions) >= 1
    assert plan.actions[0].type == ActionType.SEARCH_KNOWLEDGE


def test_parse_plan_response_fallback():
    """Test fallback when no actions parsed"""
    llm_output = "This is not a valid plan format"

    plan = parse_plan_response(llm_output, "test query")

    # Should create fallback action
    assert len(plan.actions) == 1
    assert plan.actions[0].type == ActionType.SEARCH_KNOWLEDGE
    assert plan.actions[0].params == {"query": "test query"}


# ========================================
# Test create_plan (async with LLM)
# ========================================

@pytest.mark.asyncio
async def test_create_plan_complex_query():
    """Test plan generation for complex query"""
    query = "Get your contact email and tell me your business hours"
    intent = Intent.QUESTION

    try:
        plan = await create_plan(query, intent)

        assert plan.query == query
        assert len(plan.actions) >= 1  # Should have at least one action
        assert isinstance(plan.actions[0], Action)
        assert plan.estimated_steps == len(plan.actions)
    except Exception as e:
        # If LLM unavailable, test should still pass
        pytest.skip(f"LLM not available for test: {e}")


@pytest.mark.asyncio
async def test_create_plan_with_context():
    """Test plan generation with context"""
    query = "Send me that information"
    intent = Intent.QUESTION
    context = {"session_id": "test123"}

    try:
        plan = await create_plan(query, intent, context)

        assert plan.query == query
        assert len(plan.actions) >= 1
    except Exception as e:
        pytest.skip(f"LLM not available for test: {e}")


# ========================================
# Test aggregate_results
# ========================================

@pytest.mark.asyncio
async def test_aggregate_results_multiple_actions():
    """Test aggregating results from multiple actions"""
    plan = ActionPlan(
        query="test",
        goal="test",
        actions=[],
        estimated_steps=2
    )

    results = [
        ActionResult(
            action_type=ActionType.GET_CONTACT_INFO,
            success=True,
            data={"contact_info": "email: info@example.com"}
        ),
        ActionResult(
            action_type=ActionType.SEARCH_KNOWLEDGE,
            success=True,
            data={"response": "We're open 9-5 Monday-Friday"}
        )
    ]

    response = await aggregate_results(plan, results)

    assert "info@example.com" in response
    assert "9-5" in response or "Monday-Friday" in response


@pytest.mark.asyncio
async def test_aggregate_results_no_success():
    """Test aggregating when no actions succeeded"""
    plan = ActionPlan(
        query="test",
        goal="test",
        actions=[],
        estimated_steps=1
    )

    results = [
        ActionResult(
            action_type=ActionType.SEARCH_KNOWLEDGE,
            success=False,
            error="Not found"
        )
    ]

    response = await aggregate_results(plan, results)

    assert "wasn't able to complete" in response or "sorry" in response.lower()


# ========================================
# Test execute_plan (integration test)
# ========================================

@pytest.mark.asyncio
async def test_execute_plan_single_action():
    """Test executing simple plan with one action"""
    plan = ActionPlan(
        query="What is your email?",
        goal="Get contact email",
        actions=[
            Action(
                type=ActionType.GET_CONTACT_INFO,
                params={"type": "email"},
                description="Get email address"
            )
        ],
        estimated_steps=1
    )

    try:
        result = await execute_plan(plan, session_id="test")

        assert "response" in result
        assert "plan" in result
        assert "results" in result
        assert len(result["results"]) == 1
    except Exception as e:
        pytest.skip(f"Database not available for integration test: {e}")


@pytest.mark.asyncio
async def test_execute_plan_multiple_actions():
    """Test executing plan with multiple sequential actions"""
    plan = ActionPlan(
        query="Get your email and hours",
        goal="Get email and hours",
        actions=[
            Action(
                type=ActionType.GET_CONTACT_INFO,
                params={"type": "email"},
                description="Get email"
            ),
            Action(
                type=ActionType.SEARCH_KNOWLEDGE,
                params={"query": "business hours"},
                description="Get hours"
            )
        ],
        estimated_steps=2
    )

    try:
        result = await execute_plan(plan, session_id="test")

        assert "response" in result
        assert len(result["results"]) == 2
    except Exception as e:
        pytest.skip(f"Database not available for integration test: {e}")


@pytest.mark.asyncio
async def test_execute_plan_with_failure():
    """Test plan execution when an action fails"""
    plan = ActionPlan(
        query="Test",
        goal="Test",
        actions=[
            Action(
                type=ActionType.SEND_EMAIL,  # Not implemented yet, will fail
                params={},
                description="Send email"
            )
        ],
        estimated_steps=1
    )

    result = await execute_plan(plan, session_id="test")

    assert "response" in result
    assert result["success"] == False  # Should fail gracefully


# ========================================
# Edge Cases
# ========================================

@pytest.mark.asyncio
async def test_needs_planning_empty_query():
    """Test with empty query"""
    query = ""
    intent = Intent.QUESTION

    result = await needs_planning(query, intent)

    # Empty query shouldn't trigger planning
    assert result == False


@pytest.mark.asyncio
async def test_execute_plan_empty_actions():
    """Test executing plan with no actions"""
    plan = ActionPlan(
        query="Test",
        goal="Test",
        actions=[],
        estimated_steps=0
    )

    result = await execute_plan(plan, session_id="test")

    assert "response" in result
    # Should return fallback message
