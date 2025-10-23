"""
RAG (Retrieval-Augmented Generation) service
Orchestrates the entire pipeline: embed → search → retrieve → generate
Includes intent classification for conversational queries
"""
from typing import List, Dict, Optional, Any
import random
import time
from app.services.embedding_service import get_embedding
from app.services.vectorstore_service import similarity_search
from app.services.llm_service import generate_response
from app.services.conversation_service import get_conversation_history, format_history_for_llm
from app.services.intent_service import (
    classify_intent_hybrid,
    Intent,
    should_use_rag,
    get_intent_metadata
)
from app.utils.prompts import (
    RAG_SYSTEM_PROMPT,
    FALLBACK_RESPONSE,
    GREETING_RESPONSES,
    FAREWELL_RESPONSES,
    GRATITUDE_RESPONSES,
    HELP_RESPONSE,
    CHIT_CHAT_RESPONSES,
    UNCLEAR_QUERY_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    CONVERSATIONAL_WITH_CONTEXT_PROMPT,
    CLARIFICATION_RESPONSES
)
from app.core.config import settings
from app.utils.logger import get_logger
# Phase 6: Metrics & Observability
from app.services.metrics_service import MetricsContext, record_metric, MetricType

logger = get_logger(__name__)


def preprocess_query(query: str) -> str:
    """
    Preprocess query to handle common issues:
    1. Normalize company name variations (Githaf → Githaf Consulting)
    2. Fix common misspellings

    Args:
        query: Original user query

    Returns:
        Preprocessed query
    """
    if not query or not query.strip():
        return query

    processed = query

    # 1. Normalize company name variations
    # Replace standalone "Githaf" with "Githaf Consulting" (but not if already "Githaf Consulting")
    import re
    # Match "Githaf" but not "Githaf Consulting" (case insensitive)
    processed = re.sub(r'\b(Githaf)(?!\s+Consulting)\b', r'Githaf Consulting', processed, flags=re.IGNORECASE)

    # 2. Fix common misspellings (case-insensitive replacements)
    misspelling_map = {
        # Contact-related
        r'\b(emial|emal|e-mail)\b': 'email',
        r'\b(contct|contac|contat)\b': 'contact',
        r'\b(locaton|loction|locaion)\b': 'location',
        r'\b(addres|adress)\b': 'address',
        r'\b(phne|phn)\b': 'phone',

        # Services-related
        r'\b(servce|servic|servces)\b': 'services',
        r'\b(consultin|consultng|consutling)\b': 'consulting',
        r'\b(bussiness|busines|buisness)\b': 'business',

        # Common words
        r'\b(queston|questin|qustion)\b': 'question',
        r'\b(informaton|informtion|infomation)\b': 'information',
        r'\b(avaliable|availble|avalable)\b': 'available',
        r'\b(recieve|recive)\b': 'receive',
        r'\b(responce|reponse)\b': 'response',
    }

    for pattern, replacement in misspelling_map.items():
        processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

    # Log if query was modified
    if processed != query:
        logger.info(f"Query preprocessing: '{query}' -> '{processed}'")

    return processed


async def get_conversational_response(
    intent: Intent,
    query: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate response for conversational intents (non-RAG)
    Uses conversation context for better continuity

    Args:
        intent: Detected user intent
        query: Original user query
        session_id: Optional session ID for conversation history

    Returns:
        Dict containing response and metadata
    """
    logger.info(f"Handling conversational intent: {intent.value}")

    response_text = ""

    # Handle clear template-based intents
    if intent == Intent.GREETING:
        response_text = random.choice(GREETING_RESPONSES)

    elif intent == Intent.FAREWELL:
        response_text = random.choice(FAREWELL_RESPONSES)

    elif intent == Intent.GRATITUDE:
        response_text = random.choice(GRATITUDE_RESPONSES)

    elif intent == Intent.HELP:
        response_text = HELP_RESPONSE

    elif intent == Intent.OUT_OF_SCOPE:
        response_text = OUT_OF_SCOPE_RESPONSE

    elif intent == Intent.UNCLEAR:
        # Vague query - provide context-specific clarification
        query_lower = query.lower().strip()

        # Map query to clarification category
        clarification_key = "default"
        for keyword in ["email"]:
            if keyword in query_lower:
                clarification_key = "email"
                break
        for keyword in ["pricing", "price", "cost", "payment", "fee"]:
            if keyword in query_lower:
                clarification_key = "pricing"
                break
        for keyword in ["contact", "phone", "address", "location"]:
            if keyword in query_lower:
                clarification_key = "contact"
                break
        for keyword in ["services", "service"]:
            if keyword in query_lower:
                clarification_key = "services"
                break
        for keyword in ["hours", "schedule", "availability"]:
            if keyword in query_lower:
                clarification_key = "hours"
                break

        # Select appropriate clarification response
        response_text = random.choice(CLARIFICATION_RESPONSES.get(clarification_key, CLARIFICATION_RESPONSES["default"]))

    elif intent == Intent.CHIT_CHAT:
        # For chit-chat, check if we need context-aware response
        query_lower = query.lower().strip()

        # Specific pattern responses
        if "how are you" in query_lower or "how r u" in query_lower:
            response_text = random.choice(CHIT_CHAT_RESPONSES["how_are_you"])
        elif "your name" in query_lower or "who are you" in query_lower or "what are you" in query_lower:
            response_text = random.choice(CHIT_CHAT_RESPONSES["name"])
        elif "bot" in query_lower or "robot" in query_lower or "ai" in query_lower:
            response_text = random.choice(CHIT_CHAT_RESPONSES["bot"])
        # Context-dependent responses (yes, okay, sure, etc.)
        elif session_id and query_lower in ["yes", "okay", "ok", "sure", "yep", "yeah", "yup"]:
            # Get conversation history for context
            history = await get_conversation_history(session_id, limit=3)
            if history and len(history) > 0:
                history_text = await format_history_for_llm(history)
                # Use LLM with context
                prompt = CONVERSATIONAL_WITH_CONTEXT_PROMPT.format(
                    query=query,
                    history=history_text
                )
                try:
                    response_text = await generate_response(prompt, max_tokens=100, temperature=0.7)
                except Exception as e:
                    logger.error(f"Error generating context-aware response: {e}")
                    response_text = random.choice(CHIT_CHAT_RESPONSES["default"])
            else:
                response_text = random.choice(CHIT_CHAT_RESPONSES["default"])
        else:
            # Generic chit-chat default
            response_text = random.choice(CHIT_CHAT_RESPONSES["default"])

    else:
        response_text = UNCLEAR_QUERY_RESPONSE

    # Translate conversational response if enabled (Phase 7: Translation)
    from app.services.translation_service import translate_ai_response
    response_text = await translate_ai_response(response_text, session_id=session_id)

    result = {
        "response": response_text,
        "sources": [],
        "context_found": False,
        "intent": intent.value,
        "conversational": True
    }

    # Add dialog state if available (NEW)
    if session_id:
        try:
            from app.services.dialog_state_service import get_conversation_context
            context = await get_conversation_context(session_id)
            result["dialog_state"] = context.current_state.value
        except:
            pass

    return result


async def get_rag_response(
    query: str,
    session_id: Optional[str] = None,
    include_history: bool = True,
    max_retries: int = 2  # NEW: Phase 1 - Allow retries for validation
) -> Dict[str, Any]:
    """
    Get response using RAG pipeline with intent classification and validation (Phase 1: Observation Layer)

    Args:
        query: User query
        session_id: Optional session ID for conversation context
        include_history: Whether to include conversation history
        max_retries: Maximum number of retries if validation fails (default: 2)

    Returns:
        Dict containing response, sources, and validation metadata
    """
    try:
        # Track total latency (Phase 6: Metrics)
        start_time = time.time()

        logger.info(f"Processing query: {query[:100]}...")

        # 0. Preprocess query (fix misspellings, normalize company name)
        processed_query = preprocess_query(query)

        # 1. Classify intent using hybrid approach WITH SESSION CONTEXT (NEW)
        async with MetricsContext("intent", session_id=session_id) as ctx:
            intent, confidence = await classify_intent_hybrid(processed_query, session_id=session_id)
            ctx.add_context({"intent": intent.value, "confidence": confidence})

        metadata = get_intent_metadata(intent, query)
        logger.info(f"Detected intent: {intent.value} (confidence: {confidence:.2f}) | Metadata: {metadata}")

        # 1.5 Update dialog state and check for state-specific responses (NEW)
        if session_id:
            try:
                from app.services.dialog_state_service import (
                    get_conversation_context,
                    update_conversation_state,
                    determine_state_from_intent,
                    get_contextual_response_for_state
                )

                # Get current context
                context = await get_conversation_context(session_id)

                # Determine new state based on intent and context
                new_state = determine_state_from_intent(intent.value, processed_query, context)

                # Check if this state has a specific response (e.g., AWAITING_QUESTION)
                state_response = get_contextual_response_for_state(new_state, processed_query)

                if state_response:
                    # Update state and return state-specific response
                    await update_conversation_state(
                        session_id,
                        new_state,
                        intent=intent.value
                    )

                    logger.info(f"Returning state-specific response for state: {new_state.value}")
                    return {
                        "response": state_response,
                        "sources": [],
                        "context_found": False,
                        "intent": intent.value,
                        "conversational": True,
                        "dialog_state": new_state.value  # NEW: Include state in response
                    }

                # Update state for normal processing
                await update_conversation_state(
                    session_id,
                    new_state,
                    intent=intent.value,
                    topic=None  # Could extract topic from query in future
                )

            except Exception as e:
                logger.warning(f"Error updating dialog state: {e}")
                # Continue with normal processing

        # 2. Handle conversational intents (fast path - no RAG needed)
        if not should_use_rag(intent):
            logger.info(f"Using conversational response for intent: {intent.value}")
            return await get_conversational_response(intent, processed_query, session_id)

        # 3. Check if planning needed (Phase 2: Planning Layer + Phase 2.5: Reflexive Planning)
        from app.services.planning_service import needs_planning, create_plan
        from app.services.meta_planner import execute_with_replanning

        if await needs_planning(processed_query, intent):
            logger.info("Complex query detected, using planning approach")

            # Create action plan
            plan = await create_plan(
                query=processed_query,
                intent=intent,
                context={"session_id": session_id}
            )

            # Execute plan with reflexive replanning (Phase 2.5)
            plan_result = await execute_with_replanning(plan, session_id, max_replans=2)

            # Validate final response
            from app.services.validation_service import validate_response

            validation = await validate_response(
                query=query,
                response=plan_result["response"],
                sources=[]  # Sources embedded in plan results
            )

            return {
                "response": plan_result["response"],
                "sources": [],
                "context_found": plan_result["success"],
                "intent": intent.value,
                "conversational": False,
                "planned": True,  # NEW: Indicate planned response
                "plan": plan.dict(),
                "validation": {
                    "confidence": validation["confidence"],
                    "retry_count": 0,
                    "issues": validation["issues"],
                    "is_valid": validation["is_valid"]
                }
            }

        # 4. Enrich query with semantic memory (Phase 4: Advanced Memory)
        memories = []
        if session_id:
            try:
                from app.services.memory_service import retrieve_semantic_memory

                memories = await retrieve_semantic_memory(session_id, query=processed_query, limit=3)
                if memories:
                    logger.info(f"Retrieved {len(memories)} relevant memories for query enrichment")
            except Exception as e:
                logger.warning(f"Failed to retrieve semantic memory: {e}")
                memories = []

        # 5. Continue with RAG pipeline for simple questions
        logger.info("Using RAG pipeline for question/unknown intent")

        # 6. Embed the processed query (Phase 6: Track embedding latency)
        async with MetricsContext("embedding", session_id=session_id) as ctx:
            query_embedding = await get_embedding(processed_query)

        logger.debug("Query embedded successfully")

        # 6. Adjust threshold for factual queries (hybrid search)
        # Keywords that indicate queries needing exact info (email, phone, etc.)
        query_lower = processed_query.lower()
        factual_keywords = ["email", "phone", "contact", "address", "number", "reach", "call", "location", "where", "office"]
        is_factual_query = any(keyword in query_lower for keyword in factual_keywords)

        # Use lower threshold for factual queries to ensure we find contact info
        # Use even lower threshold for email/location queries (contact info chunks may have lower similarity)
        if "email" in query_lower or "location" in query_lower or "where" in query_lower or "address" in query_lower:
            threshold = 0.20
        elif is_factual_query:
            threshold = 0.25
        else:
            threshold = settings.RAG_SIMILARITY_THRESHOLD

        if is_factual_query:
            logger.info(f"Detected factual query with keywords: {[k for k in factual_keywords if k in query_lower]}")
            logger.info(f"Using relaxed threshold: {threshold} (default: {settings.RAG_SIMILARITY_THRESHOLD})")

        # 7. Similarity search (retrieve more candidates for factual queries to allow re-ranking)
        top_k = settings.RAG_TOP_K * 2 if is_factual_query else settings.RAG_TOP_K
        logger.info(f"Calling similarity_search with top_k={top_k}, threshold={threshold}")

        # Phase 6: Track search latency
        async with MetricsContext("search", session_id=session_id) as ctx:
            relevant_docs = await similarity_search(
                query_embedding,
                top_k=top_k,
                threshold=threshold
            )
            ctx.add_context({"docs_found": len(relevant_docs) if relevant_docs else 0})

        logger.info(f"Similarity search returned {len(relevant_docs) if relevant_docs else 0} documents")

        # 8. Re-rank results for factual queries (boost documents with actual facts)
        if is_factual_query and relevant_docs:
            # Check query for specific keywords
            needs_email = "email" in query_lower
            needs_phone = "phone" in query_lower or "call" in query_lower or "number" in query_lower
            needs_location = "location" in query_lower or "where" in query_lower or "address" in query_lower or "office" in query_lower

            for doc in relevant_docs:
                content = doc.get("content", "").lower()

                # Boost score if doc contains actual email addresses (@ symbol)
                if needs_email and "@" in content:
                    doc["similarity"] = min(1.0, doc["similarity"] * 1.5)  # 50% boost
                    logger.debug(f"Boosted doc with email addresses: {doc['similarity']:.4f}")

                # Boost score if doc contains phone numbers (+ or digits)
                if needs_phone and ("+" in content or any(char.isdigit() for char in content)):
                    doc["similarity"] = min(1.0, doc["similarity"] * 1.3)  # 30% boost
                    logger.debug(f"Boosted doc with phone numbers: {doc['similarity']:.4f}")

                # Boost score if doc contains addresses (street, city, country indicators)
                if needs_location and any(word in content for word in ["street", "london", "uk", "uae", "city", "mailing address", "office:"]):
                    doc["similarity"] = min(1.0, doc["similarity"] * 1.6)  # 60% boost
                    logger.debug(f"Boosted doc with location info: {doc['similarity']:.4f}")

            # Re-sort by boosted similarity scores
            relevant_docs = sorted(relevant_docs, key=lambda x: x.get("similarity", 0), reverse=True)

            # Keep only top K after re-ranking
            relevant_docs = relevant_docs[:settings.RAG_TOP_K]
            logger.info(f"Re-ranked results for factual query, keeping top {len(relevant_docs)}")

        # 9. Check if we have relevant context
        if not relevant_docs or len(relevant_docs) == 0:
            logger.warning(f"No relevant documents found for query: '{query[:50]}...'")
            logger.warning(f"Threshold: {settings.RAG_SIMILARITY_THRESHOLD}, Top-K: {settings.RAG_TOP_K}")
            return {
                "response": FALLBACK_RESPONSE,
                "sources": [],
                "context_found": False,
                "intent": intent.value
            }

        # 10. Build context from retrieved documents
        context_parts = []
        sources = []

        for i, doc in enumerate(relevant_docs, 1):
            content = doc.get("content", "")
            similarity = doc.get("similarity", 0)
            doc_id = doc.get("id", "")

            context_parts.append(f"[Source {i}] {content}")

            sources.append({
                "id": doc_id,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "similarity": similarity
            })

        context = "\n\n".join(context_parts)

        # 11. Get conversation history (if available)
        history_text = "No previous conversation."

        if include_history and session_id:
            history = await get_conversation_history(session_id, limit=5)
            history_text = await format_history_for_llm(history)

        # 11.5. Format semantic memories for prompt (Phase 4: Advanced Memory)
        memory_text = ""
        if memories and len(memories) > 0:
            memory_parts = []
            for i, mem in enumerate(memories, 1):
                content = mem.get("content", "")
                category = mem.get("category", "context")
                memory_parts.append(f"[Fact {i}] ({category}) {content}")

            memory_text = "\n".join(memory_parts)
            logger.info(f"Including {len(memories)} semantic facts in prompt")

        # 12. Build prompt (use original query so user sees their question)
        if memory_text:
            # Include semantic memory in prompt for personalization
            prompt = f"""{RAG_SYSTEM_PROMPT.format(
                context=context,
                history=history_text,
                query=query
            )}

IMPORTANT - User Facts from Earlier in Conversation:
{memory_text}

Use these facts to personalize your response. For example:
- If user mentioned their industry, reference it naturally
- If user mentioned their company size, consider it in recommendations
- If user stated preferences, respect them
- Make the response feel like you remember the conversation context

Generate your personalized response now:"""
        else:
            # No memories, use standard prompt
            prompt = RAG_SYSTEM_PROMPT.format(
                context=context,
                history=history_text,
                query=query  # Use original query in prompt for natural response
            )

        # 13. Generate response using LLM (Phase 6: Track LLM latency)
        async with MetricsContext("llm", session_id=session_id) as ctx:
            response_text = await generate_response(prompt)

        logger.info("RAG response generated successfully")

        # 14. VALIDATE RESPONSE (Phase 1: Observation Layer + Phase 6: Track validation latency)
        from app.services.validation_service import validate_response, retry_with_adjustment

        async with MetricsContext("validation", session_id=session_id) as ctx:
            validation = await validate_response(
                query=query,
                response=response_text,
                sources=sources
            )
            ctx.add_context({"is_valid": validation["is_valid"], "confidence": validation["confidence"]})

        # 15. RETRY IF NEEDED (Phase 1: Observation Layer)
        retry_count = 0
        while not validation["is_valid"] and validation["retry_recommended"] and retry_count < max_retries:
            # Check if it's a rate limit error - don't retry in that case
            if validation.get("error_type") == "rate_limit":
                logger.warning("Rate limit detected - skipping retry to avoid wasting tokens")
                break

            retry_count += 1
            logger.warning(f"Response validation failed, retry {retry_count}/{max_retries}")
            logger.warning(f"Issues: {validation['issues']}")
            logger.warning(f"Adjustment: {validation['suggested_adjustment']}")

            # Retry with adjusted parameters
            retry_response = await retry_with_adjustment(
                query=query,
                adjustment=validation["suggested_adjustment"],
                original_threshold=threshold
            )

            # Update response and sources from retry
            response_text = retry_response.get("response", response_text)
            sources = retry_response.get("sources", sources)

            # Validate retry
            validation = await validate_response(
                query=query,
                response=response_text,
                sources=sources
            )

        # Log final validation status
        if validation["is_valid"]:
            logger.info(f"Final response validated (confidence: {validation['confidence']:.2f}, retries: {retry_count})")
        else:
            logger.warning(f"Final response still has issues after {retry_count} retries: {validation['issues']}")

        # 16. Record aggregate metrics (Phase 6: Metrics & Observability)
        total_latency_ms = (time.time() - start_time) * 1000
        await record_metric(MetricType.LATENCY_TOTAL, total_latency_ms, "ms", {
            "intent": intent.value,
            "session_id": session_id or "anonymous",
            "retry_count": retry_count,
            "context_found": True
        })
        await record_metric(MetricType.QUERY_COUNT, 1, "count", {"intent": intent.value})
        await record_metric(MetricType.INTENT_CONFIDENCE, confidence, "score", {})
        await record_metric(MetricType.VALIDATION_CONFIDENCE, validation["confidence"], "score", {})

        logger.info(f"Total query latency: {total_latency_ms:.2f}ms")

        # 16.5. Translate AI response if enabled (Phase 7: Translation)
        from app.services.translation_service import translate_ai_response
        response_text = await translate_ai_response(response_text, session_id=session_id)

        # 17. Return with validation metadata
        result = {
            "response": response_text,
            "sources": sources,
            "context_found": True,
            "intent": intent.value,
            "conversational": False,
            "validation": {  # NEW: Add validation metadata (Phase 1)
                "confidence": validation["confidence"],
                "retry_count": retry_count,
                "issues": validation["issues"],
                "is_valid": validation["is_valid"]
            }
        }

        # Add dialog state if available (NEW)
        if session_id:
            try:
                from app.services.dialog_state_service import get_conversation_context
                context = await get_conversation_context(session_id)
                result["dialog_state"] = context.current_state.value
            except:
                pass

        return result

    except Exception as e:
        logger.error(f"Error in RAG pipeline: {e}")
        return {
            "response": FALLBACK_RESPONSE,
            "sources": [],
            "context_found": False,
            "error": str(e)
        }


async def evaluate_query_quality(query: str) -> Dict[str, Any]:
    """
    Evaluate if a query is clear and answerable

    Args:
        query: User query

    Returns:
        Dict with quality metrics
    """
    # Simple heuristics for query quality
    is_too_short = len(query.split()) < 3
    is_too_long = len(query.split()) > 100
    has_question_mark = "?" in query

    quality_score = 1.0

    if is_too_short:
        quality_score -= 0.3

    if is_too_long:
        quality_score -= 0.2

    if not has_question_mark and len(query.split()) < 5:
        quality_score -= 0.1

    return {
        "score": max(0, quality_score),
        "is_clear": quality_score > 0.5,
        "suggestions": []
    }


async def process_conversation_memory(conversation_id: str, session_id: str) -> Dict[str, Any]:
    """
    Process conversation for long-term memory (Phase 4: Advanced Memory)
    Extracts semantic facts and creates summary

    Args:
        conversation_id: ID of conversation to process
        session_id: Session identifier

    Returns:
        Processing results
    """
    logger.info(f"Processing conversation {conversation_id} for memory storage")

    try:
        from app.services.memory_service import extract_semantic_facts, store_semantic_memory
        from app.services.conversation_summary_service import summarize_conversation

        # Extract semantic facts
        facts = await extract_semantic_facts(conversation_id)

        # Store facts in semantic memory
        facts_stored = 0
        if facts:
            facts_stored = await store_semantic_memory(facts, session_id)

        # Generate conversation summary
        summary = await summarize_conversation(conversation_id)

        return {
            "success": True,
            "facts_extracted": len(facts),
            "facts_stored": facts_stored,
            "summary_created": summary is not None,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error processing conversation memory: {e}")
        return {
            "success": False,
            "error": str(e)
        }
