"""
Vector store service for pgvector similarity search
"""
from typing import List, Dict, Any, Optional
from app.core.database import get_supabase_client
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def similarity_search(
    query_embedding: List[float],
    top_k: int = None,
    threshold: float = None
) -> List[Dict[str, Any]]:
    """
    Perform cosine similarity search using pgvector

    Args:
        query_embedding: Query embedding vector
        top_k: Number of results to return (default from settings)
        threshold: Minimum similarity threshold (default from settings)

    Returns:
        List[Dict]: List of matching documents with metadata
    """
    try:
        if top_k is None:
            top_k = settings.RAG_TOP_K

        if threshold is None:
            threshold = settings.RAG_SIMILARITY_THRESHOLD

        client = get_supabase_client()

        logger.info(f"Performing similarity search (top_k={top_k}, threshold={threshold})")
        logger.debug(f"Query embedding dimension: {len(query_embedding)}")

        # Call the match_documents RPC function
        # Note: query_embedding is sent as a Python list, Supabase converts it to vector type
        try:
            response = client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,  # Send as list, Supabase handles conversion
                    'match_threshold': threshold,
                    'match_count': top_k
                }
            ).execute()

            results = response.data if response.data else []

            logger.info(f"Found {len(results)} matching documents")
            if len(results) == 0:
                logger.warning(f"RPC returned 0 results. Response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
                logger.warning(f"Response data: {response.data}")

        except Exception as rpc_error:
            logger.error(f"RPC call failed: {rpc_error}")
            raise

        return results

    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        # Return empty list on error instead of failing
        return []


async def store_embedding(
    document_id: str,
    chunk_text: str,
    embedding: List[float]
) -> Dict[str, Any]:
    """
    Store an embedding in the database

    Args:
        document_id: ID of the source document
        chunk_text: Text chunk
        embedding: Embedding vector

    Returns:
        Dict: Created embedding record
    """
    try:
        client = get_supabase_client()

        data = {
            "document_id": document_id,
            "chunk_text": chunk_text,
            "embedding": embedding  # Store as list, Supabase/PostgreSQL handles vector conversion
        }

        response = client.table("embeddings").insert(data).execute()

        logger.info(f"Stored embedding for document {document_id}")

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error storing embedding: {e}")
        raise


async def store_embeddings_batch(
    embeddings_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Store multiple embeddings in batch

    Args:
        embeddings_data: List of embedding records

    Returns:
        List[Dict]: Created embedding records
    """
    try:
        client = get_supabase_client()

        # Supabase/PostgreSQL will automatically convert list to vector type
        response = client.table("embeddings").insert(embeddings_data).execute()

        logger.info(f"Stored {len(embeddings_data)} embeddings in batch")

        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Error storing batch embeddings: {e}")
        raise


async def delete_embeddings_by_document(document_id: str) -> bool:
    """
    Delete all embeddings for a document

    Args:
        document_id: Document ID

    Returns:
        bool: True if successful
    """
    try:
        client = get_supabase_client()

        response = client.table("embeddings").delete().eq("document_id", document_id).execute()

        logger.info(f"Deleted embeddings for document {document_id}")

        return True

    except Exception as e:
        logger.error(f"Error deleting embeddings: {e}")
        return False
