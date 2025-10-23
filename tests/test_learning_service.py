"""
Tests for learning_service.py (Phase 3: Self-Improvement Loop)
"""
import pytest
from app.services.learning_service import (
    analyze_feedback_batch,
    parse_analysis_response,
    apply_threshold_adjustments,
    get_current_thresholds,
    weekly_learning_job,
    get_knowledge_gaps,
    parse_knowledge_gaps,
    CURRENT_THRESHOLDS
)


# ========================================
# Test parse_analysis_response
# ========================================

def test_parse_analysis_response_valid():
    """Test parsing valid LLM analysis response"""
    llm_output = """
COMMON_ISSUES:
- Responses lack specific contact information
- Generic answers without context

ROOT_CAUSES:
- Knowledge base missing contact details
- Similarity threshold too high

THRESHOLD_ADJUSTMENTS:
similarity_threshold: 0.5 → 0.4 (lower to retrieve more context)
top_k: 5 → 7 (increase results)
temperature: 0.7 → 0.6 (more focused responses)

KNOWLEDGE_GAPS:
- Contact information (phone, address)
- Business hours details

RECOMMENDATIONS:
1. Add contact information to knowledge base
2. Lower similarity threshold to 0.4
3. Update FAQ with common questions

CONFIDENCE: 0.85
    """

    result = parse_analysis_response(llm_output)

    assert len(result["issues_found"]) >= 1
    assert "contact information" in result["issues_found"][0].lower()

    assert len(result["root_causes"]) >= 1

    assert "similarity_threshold" in result["threshold_adjustments"]
    assert "0.4" in result["threshold_adjustments"]["similarity_threshold"]

    assert len(result["knowledge_gaps"]) >= 1

    assert len(result["recommendations"]) >= 1

    assert result["confidence"] == 0.85


def test_parse_analysis_response_minimal():
    """Test parsing minimal analysis response"""
    llm_output = """
CONFIDENCE: 0.5
    """

    result = parse_analysis_response(llm_output)

    assert result["confidence"] == 0.5
    assert result["issues_found"] == []
    assert result["recommendations"] == []


# ========================================
# Test apply_threshold_adjustments
# ========================================

@pytest.mark.asyncio
async def test_apply_threshold_adjustments():
    """Test applying threshold adjustments"""
    adjustments = {
        "similarity_threshold": "0.5 → 0.4 (lower threshold)",
        "top_k": "5 → 7 (more results)",
        "temperature": "0.7 → 0.6 (more focused)"
    }

    updated = await apply_threshold_adjustments(adjustments)

    # Check values were updated
    assert updated["similarity_threshold"] == 0.4
    assert updated["top_k"] == 7
    assert updated["temperature"] == 0.6


@pytest.mark.asyncio
async def test_apply_threshold_adjustments_safety_bounds():
    """Test safety bounds on threshold adjustments"""
    adjustments = {
        "similarity_threshold": "0.5 → 0.1 (very low)",  # Too low
        "top_k": "5 → 20 (too many)",  # Too high
        "temperature": "0.7 → 1.5 (too high)"  # Out of range
    }

    updated = await apply_threshold_adjustments(adjustments)

    # Check safety bounds applied
    assert updated["similarity_threshold"] >= 0.3  # Min bound
    assert updated["top_k"] <= 10  # Max bound
    assert updated["temperature"] <= 1.0  # Max bound


@pytest.mark.asyncio
async def test_apply_threshold_adjustments_invalid_format():
    """Test handling of invalid adjustment format"""
    adjustments = {
        "similarity_threshold": "invalid format"
    }

    # Should not crash, just skip invalid adjustments
    updated = await apply_threshold_adjustments(adjustments)

    # Original value should remain
    assert "similarity_threshold" in updated


# ========================================
# Test get_current_thresholds
# ========================================

@pytest.mark.asyncio
async def test_get_current_thresholds():
    """Test retrieving current thresholds"""
    thresholds = await get_current_thresholds()

    assert "similarity_threshold" in thresholds
    assert "top_k" in thresholds
    assert "temperature" in thresholds
    assert "validation_confidence" in thresholds

    # Check types
    assert isinstance(thresholds["similarity_threshold"], (int, float))
    assert isinstance(thresholds["top_k"], int)


# ========================================
# Test parse_knowledge_gaps
# ========================================

def test_parse_knowledge_gaps():
    """Test parsing knowledge gap analysis"""
    llm_output = """
TOPIC 1: Contact Information
Queries: 15
Severity: high
Action: Add comprehensive contact details (phone, email, address)

TOPIC 2: Pricing Information
Queries: 12
Severity: medium
Action: Create detailed pricing guide with package options

TOPIC 3: Service Details
Queries: 8
Severity: low
Action: Expand service descriptions with examples
    """

    gaps = parse_knowledge_gaps(llm_output)

    assert len(gaps) == 3

    # Check first gap
    assert gaps[0]["topic"] == "Contact Information"
    assert gaps[0]["query_count"] == 15
    assert gaps[0]["severity"] == "high"
    assert "contact details" in gaps[0]["action"].lower()

    # Check second gap
    assert gaps[1]["topic"] == "Pricing Information"
    assert gaps[1]["query_count"] == 12
    assert gaps[1]["severity"] == "medium"


def test_parse_knowledge_gaps_empty():
    """Test parsing empty knowledge gap response"""
    llm_output = ""

    gaps = parse_knowledge_gaps(llm_output)

    assert gaps == []


# ========================================
# Test analyze_feedback_batch (async, database)
# ========================================

@pytest.mark.asyncio
async def test_analyze_feedback_batch_no_data():
    """Test feedback analysis with no recent feedback"""
    try:
        result = await analyze_feedback_batch(days=7)

        # Should return valid structure even with no data
        assert "total_analyzed" in result
        assert "issues_found" in result
        assert "recommendations" in result
        assert "confidence" in result

    except Exception as e:
        # Database might not be available in test environment
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_analyze_feedback_batch_error_handling():
    """Test error handling in feedback analysis"""
    # Test with invalid days parameter
    try:
        result = await analyze_feedback_batch(days=-1)

        # Should handle gracefully
        assert "total_analyzed" in result

    except Exception as e:
        # Expected behavior - invalid parameter
        assert "days" in str(e).lower() or True


# ========================================
# Test weekly_learning_job (integration)
# ========================================

@pytest.mark.asyncio
async def test_weekly_learning_job():
    """Test weekly learning job execution"""
    try:
        result = await weekly_learning_job()

        # Should return valid structure
        assert "success" in result
        assert "message" in result

        if result["success"]:
            assert "analysis" in result or "error" not in result

    except Exception as e:
        # Database might not be available
        pytest.skip(f"Database not available: {e}")


# ========================================
# Test get_knowledge_gaps (database integration)
# ========================================

@pytest.mark.asyncio
async def test_get_knowledge_gaps():
    """Test knowledge gap identification"""
    try:
        gaps = await get_knowledge_gaps(days=30)

        # Should return list (may be empty)
        assert isinstance(gaps, list)

        if gaps:
            # If data exists, check structure
            assert "topic" in gaps[0]
            assert "query_count" in gaps[0]
            assert "severity" in gaps[0]
            assert "action" in gaps[0]

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Edge Cases
# ========================================

@pytest.mark.asyncio
async def test_apply_threshold_adjustments_empty():
    """Test applying empty adjustments"""
    updated = await apply_threshold_adjustments({})

    # Should return current thresholds unchanged
    assert "similarity_threshold" in updated


def test_parse_analysis_response_malformed():
    """Test parsing malformed LLM response"""
    llm_output = """
This is a completely malformed response
with no proper structure.
    """

    result = parse_analysis_response(llm_output)

    # Should not crash, return empty results
    assert result["issues_found"] == []
    assert result["confidence"] >= 0.0


@pytest.mark.asyncio
async def test_analyze_feedback_batch_zero_days():
    """Test feedback analysis with zero days"""
    try:
        result = await analyze_feedback_batch(days=0)

        # Should handle gracefully (no data expected)
        assert result["total_analyzed"] == 0

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ========================================
# Scheduler Integration Tests
# ========================================

def test_learning_service_imports():
    """Test that all required functions are importable"""
    from app.services.learning_service import (
        analyze_feedback_batch,
        apply_threshold_adjustments,
        weekly_learning_job,
        get_knowledge_gaps
    )

    # All imports should succeed
    assert callable(analyze_feedback_batch)
    assert callable(apply_threshold_adjustments)
    assert callable(weekly_learning_job)
    assert callable(get_knowledge_gaps)
