"""
Text processing utilities for document chunking and cleaning
"""
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings
import re


def clean_text(text: str) -> str:
    """
    Clean and normalize text

    Args:
        text: Raw text

    Returns:
        str: Cleaned text
    """
    # Normalize Unicode dashes to ASCII hyphens (preserve meaning in ranges like "24–48")
    text = text.replace('–', '-')  # En-dash (U+2013)
    text = text.replace('—', '-')  # Em-dash (U+2014)
    text = text.replace('−', '-')  # Minus sign (U+2212)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep punctuation and @ symbol (for emails)
    text = re.sub(r'[^\w\s.,!?;:()\-\'\""@]', '', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[str]:
    """
    Split text into chunks for embedding

    Args:
        text: Text to split
        chunk_size: Maximum chunk size (default from settings)
        chunk_overlap: Overlap between chunks (default from settings)

    Returns:
        List[str]: List of text chunks
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE

    if chunk_overlap is None:
        chunk_overlap = settings.CHUNK_OVERLAP

    # Create text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""],
        length_function=len
    )

    # Split text
    chunks = splitter.split_text(text)

    # Clean each chunk
    chunks = [clean_text(chunk) for chunk in chunks if chunk.strip()]

    return chunks


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text (simple implementation)

    Args:
        text: Input text
        max_keywords: Maximum number of keywords

    Returns:
        List[str]: List of keywords
    """
    # Convert to lowercase
    text = text.lower()

    # Remove stopwords (basic list)
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'it', 'its', 'their', 'them', 'they'
    }

    # Extract words
    words = re.findall(r'\b\w+\b', text)

    # Filter stopwords and short words
    keywords = [w for w in words if w not in stopwords and len(w) > 3]

    # Count frequency
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top keywords
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [word for word, freq in sorted_keywords[:max_keywords]]
