"""
Pytest configuration and fixtures
"""
import pytest
import sys
import os

# Add parent directory to path so tests can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing"""
    from unittest.mock import MagicMock
    client = MagicMock()
    return client


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing"""
    return {
        "id": "test-conversation-id",
        "session_id": "test-session-id",
        "created_at": "2025-01-15T10:00:00Z",
        "last_message_at": "2025-01-15T10:05:00Z"
    }


@pytest.fixture
def sample_validation_result():
    """Sample validation result for testing"""
    return {
        "is_valid": True,
        "confidence": 0.9,
        "issues": [],
        "retry_recommended": False,
        "suggested_adjustment": ""
    }
