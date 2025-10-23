"""
Semantic Intent Matching using Embeddings
Uses semantic similarity to classify intents when pattern matching is uncertain

This provides better accuracy for paraphrased queries and edge cases.
"""
from typing import Dict, List, Tuple, Optional
from app.services.embedding_service import get_embedding
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Intent example embeddings (pre-computed and cached)
# These are representative examples for each intent category
INTENT_EXAMPLES = {
    "help": [
        "What are you?",
        "What can you do?",
        "Who are you?",
        "What is this chatbot?",
        "Help me understand what you do",
        "What are your capabilities?",
        "What is your purpose?"
    ],
    "question": [
        "What are your response times?",
        "What are your prices?",
        "What services do you offer?",
        "How do I contact you?",
        "Where are you located?",
        "What are your business hours?",
        "Tell me about your services",
        "How much does it cost?",
        "When are you open?",
        "What's your email address?"
    ],
    "greeting": [
        "Hello",
        "Hi there",
        "Good morning",
        "Hey",
        "Greetings"
    ],
    "farewell": [
        "Goodbye",
        "Bye",
        "See you later",
        "Take care",
        "Have a good day"
    ],
    "gratitude": [
        "Thank you",
        "Thanks",
        "I appreciate it",
        "Much appreciated",
        "Thanks a lot"
    ],
    "chit_chat": [
        "How are you?",
        "What's your name?",
        "Are you a bot?",
        "Are you real?",
        "Nice to meet you"
    ],
    "out_of_scope": [
        "What's the weather today?",
        "Who is the president?",
        "Tell me a joke",
        "What's 2+2?",
        "Who won the game?"
    ]
}

# Cache for pre-computed embeddings (loaded once at startup)
_intent_embedding_cache: Dict[str, List[np.ndarray]] = {}
_cache_initialized = False


async def initialize_intent_embeddings():
    """
    Pre-compute embeddings for all intent examples
    This is called once at startup to improve performance
    """
    global _cache_initialized

    if _cache_initialized:
        logger.debug("Intent embeddings already initialized")
        return

    logger.info("Initializing semantic intent matcher...")

    for intent, examples in INTENT_EXAMPLES.items():
        embeddings = []
        for example in examples:
            try:
                emb = await get_embedding(example)
                embeddings.append(np.array(emb))
            except Exception as e:
                logger.warning(f"Failed to embed example '{example}': {e}")
                continue

        _intent_embedding_cache[intent] = embeddings
        logger.debug(f"Cached {len(embeddings)} embeddings for intent: {intent}")

    _cache_initialized = True
    logger.info(f"Loaded {len(_intent_embedding_cache)} intent categories with semantic embeddings")


async def match_intent_semantically(
    query: str,
    threshold: float = 0.75,
    top_k: int = 3
) -> Tuple[Optional[str], float]:
    """
    Match query to intent using semantic similarity

    Args:
        query: User query
        threshold: Minimum similarity score (0.0-1.0)
        top_k: Number of top matches to consider

    Returns:
        Tuple of (intent_name, similarity_score) or (None, 0.0) if no match
    """
    # Ensure embeddings are loaded
    if not _cache_initialized:
        await initialize_intent_embeddings()

    if not _intent_embedding_cache:
        logger.error("Intent embedding cache is empty")
        return None, 0.0

    # Embed query
    try:
        query_embedding = np.array(await get_embedding(query))
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return None, 0.0

    # Track best matches
    best_matches = []

    # Compare to all intent examples
    for intent, example_embeddings in _intent_embedding_cache.items():
        for example_emb in example_embeddings:
            # Cosine similarity
            similarity = np.dot(query_embedding, example_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(example_emb)
            )

            best_matches.append((intent, similarity))

    # Sort by similarity (descending)
    best_matches.sort(key=lambda x: x[1], reverse=True)

    # Get top match
    if best_matches and best_matches[0][1] >= threshold:
        best_intent, best_score = best_matches[0]
        logger.info(f"Semantic match: '{query[:50]}...' -> {best_intent} ({best_score:.3f})")
        return best_intent, best_score

    # No match above threshold
    if best_matches:
        logger.debug(f"No semantic match above threshold ({threshold}). Best was: {best_matches[0][0]} ({best_matches[0][1]:.3f})")

    return None, 0.0


async def get_intent_confidence_distribution(
    query: str
) -> Dict[str, float]:
    """
    Get similarity scores for all intents (useful for debugging)

    Args:
        query: User query

    Returns:
        Dictionary of intent -> similarity score
    """
    if not _cache_initialized:
        await initialize_intent_embeddings()

    try:
        query_embedding = np.array(await get_embedding(query))
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return {}

    intent_scores = {}

    for intent, example_embeddings in _intent_embedding_cache.items():
        # Get max similarity across all examples for this intent
        max_similarity = 0.0
        for example_emb in example_embeddings:
            similarity = np.dot(query_embedding, example_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(example_emb)
            )
            max_similarity = max(max_similarity, similarity)

        intent_scores[intent] = max_similarity

    return intent_scores


async def explain_intent_match(query: str) -> str:
    """
    Get detailed explanation of how query matched to intent

    Args:
        query: User query

    Returns:
        Human-readable explanation
    """
    scores = await get_intent_confidence_distribution(query)

    # Sort by score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    explanation = f"Intent matching for: '{query}'\n\n"
    explanation += "Similarity scores:\n"

    for intent, score in sorted_scores:
        percentage = score * 100
        bar = "█" * int(percentage / 5)  # Bar chart
        explanation += f"  {intent:15} {score:.3f} ({percentage:.1f}%) {bar}\n"

    best_intent, best_score = sorted_scores[0]
    explanation += f"\nBest match: {best_intent} ({best_score:.3f})"

    return explanation


# Utility function for testing
async def test_semantic_matching():
    """Test semantic intent matching with sample queries"""

    # Initialize embeddings
    await initialize_intent_embeddings()

    test_queries = [
        "What are your response times?",  # Should match QUESTION
        "What are you?",  # Should match HELP
        "How much do you charge?",  # Should match QUESTION
        "What can you help me with?",  # Should match HELP
        "Good morning",  # Should match GREETING
        "Thanks!",  # Should match GRATITUDE
        "How's the weather?",  # Should match OUT_OF_SCOPE
        "I have a question",  # Should match CHIT_CHAT or HELP
    ]

    print("\n" + "="*80)
    print("SEMANTIC INTENT MATCHING TESTS")
    print("="*80 + "\n")

    for query in test_queries:
        intent, score = await match_intent_semantically(query, threshold=0.70)
        print(f"Query: '{query}'")
        print(f"  Intent: {intent or 'No match'}")
        print(f"  Score: {score:.3f}")

        # Show detailed scores
        scores = await get_intent_confidence_distribution(query)
        top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top 3: {', '.join([f'{i}({s:.2f})' for i, s in top_3])}")
        print()

    print("="*80 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_semantic_matching())
