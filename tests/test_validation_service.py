"""
Unit tests for validation_service
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.validation_service import parse_validation_response


@pytest.mark.unit
def test_parse_validation_response_valid():
    """Test parsing a valid validation response"""
    response_text = """
    ANSWERS_QUESTION: yes
    IS_GROUNDED: yes
    HAS_HALLUCINATION: no
    IS_CONCISE: yes
    IS_PRECISE: yes
    CONFIDENCE: 0.95
    RETRY: no
    ADJUSTMENT: None
    """
    
    result = parse_validation_response(response_text)
    
    assert result["is_valid"] == True
    assert result["confidence"] == 0.95
    assert result["retry_recommended"] == False
    assert len(result["issues"]) == 0


@pytest.mark.unit
def test_parse_validation_response_invalid():
    """Test parsing an invalid validation response"""
    response_text = """
    ANSWERS_QUESTION: no
    IS_GROUNDED: no
    HAS_HALLUCINATION: yes
    IS_CONCISE: yes
    IS_PRECISE: no
    CONFIDENCE: 0.3
    RETRY: yes
    ADJUSTMENT: Lower threshold and search more documents
    """
    
    result = parse_validation_response(response_text)
    
    assert result["is_valid"] == False
    assert result["confidence"] == 0.3
    assert result["retry_recommended"] == True
    assert "doesn't answer question" in result["issues"]
    assert "not grounded in sources" in result["issues"]
    assert "hallucination detected" in result["issues"]
    assert "lacks precision" in result["issues"]
    assert result["suggested_adjustment"] == "Lower threshold and search more documents"


@pytest.mark.unit
def test_parse_validation_response_low_confidence():
    """Test that low confidence triggers invalid status"""
    response_text = """
    ANSWERS_QUESTION: yes
    IS_GROUNDED: yes
    HAS_HALLUCINATION: no
    IS_CONCISE: yes
    IS_PRECISE: yes
    CONFIDENCE: 0.5
    RETRY: no
    ADJUSTMENT:
    """
    
    result = parse_validation_response(response_text)
    
    assert result["is_valid"] == False
    assert result["confidence"] == 0.5
    assert "low confidence" in result["issues"]
