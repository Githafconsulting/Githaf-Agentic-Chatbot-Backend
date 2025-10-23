"""
Test vector search with detailed logging
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.services.embedding_service import get_embedding
from app.services.vectorstore_service import similarity_search
from app.core.config import settings


async def test_vector_search():
    """Test vector search with sample query"""

    query = "What services does Githaf offer?"

    print("=" * 60)
    print("  Vector Search Test")
    print("=" * 60)
    print()
    print(f"Query: {query}")
    print(f"Threshold: {settings.RAG_SIMILARITY_THRESHOLD}")
    print(f"Top K: {settings.RAG_TOP_K}")
    print()

    # Generate embedding
    print("Generating query embedding...")
    query_embedding = await get_embedding(query)
    print(f"Embedding dimension: {len(query_embedding)}")
    print(f"First 5 values: {query_embedding[:5]}")
    print()

    # Perform similarity search
    print("Performing similarity search...")
    results = await similarity_search(
        query_embedding,
        top_k=settings.RAG_TOP_K,
        threshold=settings.RAG_SIMILARITY_THRESHOLD
    )

    print(f"Found {len(results)} results")
    print()

    if results:
        print("Results:")
        print("-" * 60)
        for i, result in enumerate(results, 1):
            similarity = result.get('similarity', 0)
            chunk_text = result.get('chunk_text', '')
            print(f"\n[{i}] Similarity: {similarity:.4f}")
            print(f"Full result keys: {result.keys()}")
            print(f"Full result: {result}")
            if chunk_text:
                print(f"Text: {chunk_text[:200]}...")
            else:
                print("WARNING: chunk_text is empty!")
            print()
    else:
        print("No results found!")
        print()
        print("Possible issues:")
        print("1. Similarity threshold too high (current: {})".format(settings.RAG_SIMILARITY_THRESHOLD))
        print("2. No embeddings in database")
        print("3. Query embedding not matching stored embeddings")
        print()

        # Try with lower threshold
        print("Retrying with threshold 0.0 (no filtering)...")
        results_no_filter = await similarity_search(
            query_embedding,
            top_k=settings.RAG_TOP_K,
            threshold=0.0
        )

        print(f"Found {len(results_no_filter)} results without threshold")

        if results_no_filter:
            print("\nTop results (unfiltered):")
            print("-" * 60)
            for i, result in enumerate(results_no_filter, 1):
                similarity = result.get('similarity', 0)
                chunk_text = result.get('chunk_text', '')
                print(f"\n[{i}] Similarity: {similarity:.4f}")
                print(f"Text: {chunk_text[:150]}...")


if __name__ == "__main__":
    asyncio.run(test_vector_search())
