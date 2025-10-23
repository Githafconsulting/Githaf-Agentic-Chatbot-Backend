"""
Embedding service using Sentence Transformers
"""
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Load model once at module level (singleton pattern)
_model: SentenceTransformer = None


def get_model() -> SentenceTransformer:
    """
    Get or load the embedding model

    Returns:
        SentenceTransformer: Loaded model
    """
    global _model

    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")

    return _model


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text

    Args:
        text: Input text

    Returns:
        List[float]: Embedding vector
    """
    try:
        model = get_model()
        embedding = model.encode(text, convert_to_tensor=False)

        # Convert to list
        embedding_list = embedding.tolist()

        logger.debug(f"Generated embedding for text (length: {len(text)})")

        return embedding_list

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (batch processing)

    Args:
        texts: List of input texts

    Returns:
        List[List[float]]: List of embedding vectors
    """
    try:
        model = get_model()
        embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=True)

        # Convert to list of lists
        embeddings_list = embeddings.tolist()

        logger.info(f"Generated embeddings for {len(texts)} texts")

        return embeddings_list

    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise
