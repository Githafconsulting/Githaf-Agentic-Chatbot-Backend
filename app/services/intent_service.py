"""
Intent Classification Service
Detects user intent to route queries appropriately before RAG pipeline
Uses hybrid approach: fast pattern matching + LLM fallback for ambiguous cases

Enhanced with context-aware classification using dialog state tracking.
"""
import re
from typing import Dict, Optional, List, Tuple
from enum import Enum
import random
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Intent(str, Enum):
    """Possible user intents"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    GRATITUDE = "gratitude"
    HELP = "help"
    QUESTION = "question"
    CHIT_CHAT = "chit_chat"
    OUT_OF_SCOPE = "out_of_scope"
    UNCLEAR = "unclear"  # Needs clarification (vague queries like "email", "pricing", "contact")
    UNKNOWN = "unknown"


# Intent detection patterns
INTENT_PATTERNS = {
    Intent.GREETING: [
        r"^hi\b",
        r"^hello\b",
        r"^hey\b",
        r"^good\s+(morning|afternoon|evening|day)",
        r"^greetings\b",
        r"^howdy\b",
        r"^what'?s\s+up",
        r"^yo\b",
        r"^hiya\b",
        r"^salut\b",  # French
        r"^bonjour\b",  # French
        r"^hola\b",  # Spanish
        r"^guten\s+tag\b",  # German
        r"^marhaba\b",  # Arabic
    ],
    Intent.FAREWELL: [
        r"^bye\b",
        r"^goodbye\b",
        r"^see\s+you",
        r"^farewell\b",
        r"^take\s+care",
        r"^good\s+night",
        r"^have\s+a\s+good",
        r"^talk\s+to\s+you\s+later",
        r"^ttyl\b",
        r"^cya\b",
        r"^au\s+revoir\b",  # French
        r"^adios\b",  # Spanish
        r"^tschüss\b",  # German
        r"^ma'?a?\s+salama\b",  # Arabic
        # Simple negative responses (after "anything else?" type questions)
        r"^no\b",
        r"^nope\b",
        r"^no\s+thanks\b",
        r"^no\s+thank\s+you\b",
        r"^i'?m\s+good\b",
        r"^all\s+good\b",
    ],
    Intent.GRATITUDE: [
        r"^thank",
        r"^thanks",
        r"^thx\b",
        r"\bappreciate",  # Matches "appreciate" or "I appreciate"
        r"^grateful",
        r"^merci\b",  # French
        r"^gracias\b",  # Spanish
        r"^danke\b",  # German
        r"^shukran\b",  # Arabic
        r"^i\s+appreciate",
        r"^much\s+appreciated",
        r"^highly\s+appreciated",
    ],
    Intent.HELP: [
        r"^help\b",
        r"^what\s+can\s+you\s+do\s*\?*$",  # Only "what can you do?" (nothing after)
        r"^how\s+can\s+you\s+help",
        r"^what\s+are\s+you\s+for\s*\?*$",  # Only "what are you for?"
        r"^what\s+is\s+this\s*(chatbot|bot|assistant)?\s*\?*$",  # "what is this?" or "what is this chatbot?"
        r"^who\s+are\s+you\s*\?*$",  # Only "who are you?" (nothing after)
        r"^what\s+are\s+you\s*\?*$",  # Only "what are you?" (nothing after)
        r"^are\s+you\s+(a\s+)?(bot|chatbot|assistant|ai)",  # "are you a bot?"
        r"^can\s+you\s+help(\s+me)?\s*\?*$",  # "can you help?" or "can you help me?"
        r"^i\s+need\s+help\s*\?*$",
        r"^assist(\s+me)?\s*\?*$",
        r"^show\s+me\s+what",
        r"^commands\b",
        r"^options\b",
        r"^can\s+i\s+ask",  # "can I ask you a question?"
        r"^may\s+i\s+ask",  # "may I ask a question?"
        r"^could\s+i\s+ask",  # "could I ask something?"
    ],
    Intent.CHIT_CHAT: [
        r"^how\s+are\s+you",
        r"^what'?s\s+your\s+name",
        r"^are\s+you\s+(a\s+)?bot",
        r"^are\s+you\s+(a\s+)?robot",
        r"^are\s+you\s+real",
        r"^nice\s+to\s+meet",
        r"^how\s+is\s+it\s+going",
        r"^how\s+do\s+you\s+do",
        r"^tell\s+me\s+(a\s+)?joke",
        r"^make\s+me\s+laugh",
    ],
}


async def classify_intent_with_llm(query: str) -> Tuple[str, float]:
    """
    Use LLM to classify ambiguous queries

    Args:
        query: User input text

    Returns:
        Tuple of (classification, confidence)
        classification: "CONVERSATIONAL", "KNOWLEDGE_SEEKING", or "AMBIGUOUS"
        confidence: 0.0 to 1.0
    """
    try:
        from app.services.llm_service import generate_response
        from app.utils.prompts import INTENT_CLASSIFICATION_PROMPT

        # Build classification prompt
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)

        # Get LLM classification (should be one word)
        response = await generate_response(prompt, max_tokens=10, temperature=0.1)
        classification = response.strip().upper()

        # Validate response
        valid_classifications = ["CONVERSATIONAL", "KNOWLEDGE_SEEKING", "OUT_OF_SCOPE", "AMBIGUOUS"]
        if classification not in valid_classifications:
            # Try to extract from response
            for valid in valid_classifications:
                if valid in classification:
                    classification = valid
                    break
            else:
                logger.warning(f"LLM returned invalid classification: {response}")
                return "AMBIGUOUS", 0.5

        # Assign confidence based on classification
        confidence_map = {
            "CONVERSATIONAL": 0.8,
            "KNOWLEDGE_SEEKING": 0.9,  # Higher confidence for knowledge-seeking
            "OUT_OF_SCOPE": 0.85,  # High confidence for out-of-scope
            "AMBIGUOUS": 0.3
        }

        confidence = confidence_map.get(classification, 0.5)
        logger.info(f"LLM classified '{query[:50]}...' as {classification} (confidence: {confidence})")

        return classification, confidence

    except Exception as e:
        logger.error(f"Error in LLM intent classification: {e}")
        return "AMBIGUOUS", 0.0


def is_about_chatbot(query: str) -> bool:
    """
    Determine if question is about the chatbot itself vs the company/services

    Used to distinguish:
    - "What are you?" (about chatbot) → HELP
    - "What are your response times?" (about company) → QUESTION

    Args:
        query: User input text

    Returns:
        True if question is about chatbot, False if about company
    """
    query_lower = query.lower().strip()

    # Extract subject after "your" or "you"
    # Examples:
    # "What are YOU?" → subject: None (about chatbot)
    # "What are YOUR response times?" → subject: "response times" (about company)

    # Chatbot-related subjects (when after "your")
    chatbot_subjects = [
        "name", "purpose", "function", "capabilities", "features",
        "job", "role", "what you do", "how you work", "limitations"
    ]

    # Company-related subjects (when after "your")
    company_subjects = [
        "response time", "response times", "prices", "pricing", "cost", "costs",
        "services", "service", "offerings", "products", "solutions",
        "business hours", "hours", "availability", "schedule",
        "location", "address", "office", "offices",
        "team", "staff", "employees", "experts", "consultants",
        "process", "processes", "approach", "methodology",
        "contact", "email", "phone", "number",
        "experience", "portfolio", "clients", "projects",
        "rates", "fees", "packages", "plans"
    ]

    # Check for explicit chatbot references
    if any(word in query_lower for word in ["you are", "you're", "what are you", "who are you", "are you a"]):
        # "What are you?" → about chatbot
        # "What are you doing?" → about chatbot
        # But "What are your prices?" → about company
        if "your" in query_lower:
            # Check what comes after "your"
            for company_subject in company_subjects:
                if company_subject in query_lower:
                    return False  # About company
            # If "your" but no company subject, likely about chatbot
            # "your name", "your purpose", etc.
            for chatbot_subject in chatbot_subjects:
                if chatbot_subject in query_lower:
                    return True
        # Just "you" without "your" → about chatbot
        return True

    # Check for "your X" pattern
    if "your" in query_lower or "you" in query_lower:
        # Check if it's about company
        for company_subject in company_subjects:
            if company_subject in query_lower:
                return False  # About company

        # Check if it's about chatbot
        for chatbot_subject in chatbot_subjects:
            if chatbot_subject in query_lower:
                return True  # About chatbot

    # Default: if unclear, assume it's a question (about company)
    # This is safer - we'd rather send to RAG than give wrong help message
    return False


def classify_intent(query: str) -> Intent:
    """
    Classify user intent based on query patterns

    Args:
        query: User input text

    Returns:
        Detected intent enum
    """
    if not query or not query.strip():
        return Intent.UNKNOWN

    # Normalize query
    normalized = query.lower().strip()

    # Remove punctuation for matching
    clean_query = re.sub(r'[!?.,:;]+$', '', normalized)

    # Check for vague queries first (before pattern matching)
    if is_vague_query(query):
        return Intent.UNCLEAR

    # BEFORE pattern matching: Check if HELP-like pattern but about company
    # Example: "What are your response times?" should NOT be HELP
    if re.search(r"^what\s+are\s+you", clean_query):
        if not is_about_chatbot(query):
            # It's a "what are your X" question about company → QUESTION
            return Intent.QUESTION

    if re.search(r"^who\s+are\s+you", clean_query):
        if not is_about_chatbot(query):
            # It's a "who are your X" question about company → QUESTION
            return Intent.QUESTION

    # Check each intent pattern
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, clean_query, re.IGNORECASE):
                return intent

    # Check if it's a question (fallback heuristic)
    if is_question(query):
        return Intent.QUESTION

    return Intent.UNKNOWN


def is_question(query: str) -> bool:
    """
    Determine if query is a question

    Args:
        query: User input text

    Returns:
        True if query appears to be a question
    """
    query = query.strip()

    # Has question mark
    if '?' in query:
        return True

    # Starts with question words
    question_starters = [
        'what', 'when', 'where', 'who', 'whom', 'whose', 'why', 'which',
        'how', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does',
        'did', 'will', 'may', 'might', 'tell', 'explain', 'describe'
    ]

    first_word = query.lower().split()[0] if query else ''
    return first_word in question_starters


def is_generic_query(query: str) -> bool:
    """
    Determine if query is too generic for RAG search

    Args:
        query: User input text

    Returns:
        True if query is very short/generic
    """
    words = query.strip().split()
    return len(words) <= 3 and not is_question(query)


def is_vague_query(query: str) -> bool:
    """
    Determine if query is vague and needs clarification
    Examples: "email", "pricing", "contact", "services", "info"

    Args:
        query: User input text

    Returns:
        True if query needs clarification
    """
    query_normalized = query.lower().strip()
    words = query_normalized.split()

    # Single-word vague queries (common topics without context)
    vague_keywords = [
        'email', 'contact', 'phone', 'address', 'location',
        'pricing', 'price', 'cost', 'payment', 'fee',
        'services', 'service', 'help', 'info', 'information',
        'hours', 'schedule', 'availability', 'team', 'about',
        'details', 'more', 'website', 'demo', 'trial'
    ]

    # Check if it's a single vague word or very short (1-2 words) without question structure
    if len(words) <= 2 and not is_question(query):
        # Check if any word matches vague keywords
        for word in words:
            if word in vague_keywords:
                return True

    return False


def get_intent_metadata(intent: Intent, query: str) -> Dict:
    """
    Get additional metadata about the detected intent

    Args:
        intent: Detected intent
        query: Original query

    Returns:
        Metadata dictionary
    """
    return {
        "intent": intent.value,
        "requires_rag": intent in [Intent.QUESTION, Intent.UNKNOWN],
        "requires_llm": intent == Intent.CHIT_CHAT,
        "can_use_template": intent in [Intent.GREETING, Intent.FAREWELL, Intent.GRATITUDE, Intent.HELP],
        "query_length": len(query.split()),
        "is_conversational": intent not in [Intent.QUESTION, Intent.UNKNOWN]
    }


async def classify_intent_hybrid(
    query: str,
    use_llm_fallback: bool = True,
    session_id: Optional[str] = None  # NEW: Session ID for context awareness
) -> Tuple[Intent, float]:
    """
    Hybrid intent classification: pattern matching + LLM fallback + context awareness

    Strategy:
    1. Check dialog state for context overrides (e.g., AWAITING_QUESTION state)
    2. Try fast pattern matching
    3. If result is UNKNOWN or ambiguous, use LLM for better accuracy
    4. Return intent with confidence score

    Args:
        query: User input text
        use_llm_fallback: Whether to use LLM for ambiguous cases (default: True)
        session_id: Session ID for context-aware classification (optional)

    Returns:
        Tuple of (Intent, confidence_score)
    """
    # Step 0: Check for context-based intent override (NEW)
    if session_id:
        try:
            from app.services.dialog_state_service import (
                get_conversation_context,
                should_override_intent_with_context
            )

            # Get conversation context
            context = await get_conversation_context(session_id)

            # Check if we should override based on state
            override_intent_str = should_override_intent_with_context(
                context.current_state,
                "",  # Don't have detected intent yet
                query
            )

            if override_intent_str:
                # Map string to Intent enum
                try:
                    override_intent = Intent(override_intent_str.lower())
                    logger.info(f"Context override: {context.current_state.value} → {override_intent.value}")
                    return override_intent, 0.9  # High confidence from context
                except ValueError:
                    logger.warning(f"Could not map override intent: {override_intent_str}")

        except Exception as e:
            logger.warning(f"Error checking dialog state: {e}")
            # Continue with normal classification

    # Step 1: Fast pattern matching
    pattern_intent = classify_intent(query)

    # High-confidence pattern matches (don't need LLM)
    if pattern_intent in [Intent.GREETING, Intent.FAREWELL, Intent.GRATITUDE]:
        logger.info(f"Pattern match: {pattern_intent.value} (high confidence)")
        return pattern_intent, 0.95

    # Vague queries that need clarification (high confidence)
    if pattern_intent == Intent.UNCLEAR:
        logger.info(f"Vague query detected: needs clarification")
        return pattern_intent, 0.9

    # Medium-confidence matches (may benefit from LLM verification)
    if pattern_intent in [Intent.HELP, Intent.CHIT_CHAT]:
        logger.info(f"Pattern match: {pattern_intent.value} (medium confidence)")
        return pattern_intent, 0.75

    # Low-confidence or ambiguous (use semantic matching + LLM fallback)
    if pattern_intent in [Intent.QUESTION, Intent.UNKNOWN] and use_llm_fallback:
        # Try semantic matching first (faster than LLM)
        try:
            from app.services.semantic_intent_matcher import match_intent_semantically

            semantic_intent_str, semantic_score = await match_intent_semantically(query, threshold=0.75)

            if semantic_intent_str and semantic_score >= 0.75:
                # Good semantic match - map to Intent enum
                try:
                    semantic_intent = Intent(semantic_intent_str)
                    logger.info(f"Semantic match: {semantic_intent.value} ({semantic_score:.2f})")
                    return semantic_intent, semantic_score
                except ValueError:
                    logger.warning(f"Could not map semantic intent: {semantic_intent_str}")

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")

        # If semantic matching didn't work, fall back to LLM
        logger.info(f"Pattern unclear ({pattern_intent.value}), using LLM classification...")

        try:
            llm_classification, llm_confidence = await classify_intent_with_llm(query)

            # Map LLM classification to Intent enum
            if llm_classification == "CONVERSATIONAL":
                # Conversational intent - use chit-chat response
                return Intent.CHIT_CHAT, llm_confidence
            elif llm_classification == "KNOWLEDGE_SEEKING":
                # Knowledge-seeking - use RAG pipeline
                return Intent.QUESTION, llm_confidence
            elif llm_classification == "OUT_OF_SCOPE":
                # Out of scope - polite redirect
                return Intent.OUT_OF_SCOPE, llm_confidence
            else:  # AMBIGUOUS
                # Still unclear - default to QUESTION to be safe
                logger.warning(f"LLM also ambiguous, defaulting to QUESTION")
                return Intent.QUESTION, 0.5

        except Exception as e:
            logger.error(f"LLM fallback failed: {e}, using pattern result")
            return pattern_intent, 0.4

    # Return pattern-based result
    return pattern_intent, 0.6


def should_use_rag(intent: Intent) -> bool:
    """
    Determine if query should go through RAG pipeline

    Args:
        intent: Detected intent

    Returns:
        True if RAG pipeline should be used
    """
    return intent in [Intent.QUESTION, Intent.UNKNOWN]


def get_suggested_topics() -> List[str]:
    """
    Get list of suggested conversation topics

    Returns:
        List of suggested topics the bot can answer
    """
    return [
        "Our consulting services",
        "How to contact us",
        "Business hours and availability",
        "Project requirements",
        "Pricing and packages",
        "Our expertise and experience",
        "Client success stories",
        "Getting started with a project"
    ]


# Utility function for testing
def test_intent_classification():
    """Test the intent classifier with sample queries"""
    test_queries = [
        ("Hello", Intent.GREETING),
        ("Hi there!", Intent.GREETING),
        ("Good morning", Intent.GREETING),
        ("Bye", Intent.FAREWELL),
        ("Thank you so much", Intent.GRATITUDE),
        ("Thanks!", Intent.GRATITUDE),
        ("Help", Intent.HELP),
        ("What can you do?", Intent.HELP),
        ("How are you?", Intent.CHIT_CHAT),
        ("What services do you offer?", Intent.QUESTION),
        ("Tell me about pricing", Intent.QUESTION),
        ("Can you help me with a project?", Intent.QUESTION),
    ]

    print("Intent Classification Tests:")
    print("-" * 60)

    for query, expected in test_queries:
        detected = classify_intent(query)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{query}' → {detected.value} (expected: {expected.value})")

    print("-" * 60)


if __name__ == "__main__":
    test_intent_classification()
