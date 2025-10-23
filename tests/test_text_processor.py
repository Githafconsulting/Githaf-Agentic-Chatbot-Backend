"""
Unit tests for text processing utilities
"""
import pytest
from app.utils.text_processor import chunk_text


@pytest.mark.unit
def test_chunk_text_basic():
    """Test basic text chunking"""
    text = "A" * 1000  # 1000 character string
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    # Check overlap exists
    if len(chunks) > 1:
        assert chunks[0][-50:] == chunks[1][:50]


@pytest.mark.unit
def test_chunk_text_short():
    """Test chunking text shorter than chunk size"""
    text = "Short text"
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.unit
def test_chunk_text_empty():
    """Test chunking empty text"""
    text = ""
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == "")
