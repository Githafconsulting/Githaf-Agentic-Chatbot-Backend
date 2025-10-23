"""
Response Validation Service
Assesses quality of generated responses using LLM
Implements self-observation for the agentic chatbot (Phase 1)
"""
from typing import Dict, List, Optional
import time
from app.services.llm_service import generate_response
from app.utils.prompts import VALIDATION_PROMPT
from app.utils.logger import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)


async def validate_response(
    query: str,
    response: str,
    sources: List[Dict],
    threshold: float = 0.7,
    message_id: Optional[str] = None
) -> Dict:
    """
    Use LLM to assess response quality

    Args:
        query: Original user query
        response: Generated response
        sources: Retrieved document sources
        threshold: Minimum confidence score (0-1)
        message_id: UUID of the message being validated (for logging)

    Returns:
        {
            "is_valid": bool,
            "confidence": float,
            "issues": List[str],
            "retry_recommended": bool,
            "suggested_adjustment": str
        }
    """
    # Track validation latency
    start_time = time.time()

    # Build validation prompt
    sources_text = "\n".join([f"- {s.get('content', '')[:100]}..." for s in sources]) if sources else "No sources used"

    prompt = VALIDATION_PROMPT.format(
        query=query,
        response=response,
        sources=sources_text
    )

    # Get LLM assessment
    try:
        assessment_text = await generate_response(prompt, max_tokens=200, temperature=0.1)

        # Parse structured response
        assessment = parse_validation_response(assessment_text)

        # Calculate latency
        validation_latency_ms = int((time.time() - start_time) * 1000)

        # Log if issues detected
        if not assessment["is_valid"]:
            logger.warning(f"Response validation failed for query: '{query[:50]}...'")
            logger.warning(f"Issues detected: {assessment['issues']}")
        else:
            logger.info(f"Response validated successfully (confidence: {assessment['confidence']:.2f})")

        # Add latency to assessment for logging
        assessment["validation_latency_ms"] = validation_latency_ms

        # Log to database (Phase 1: Observation Layer)
        if message_id:
            await _log_validation_result(
                message_id=message_id,
                is_valid=assessment["is_valid"],
                confidence=assessment["confidence"],
                issues=assessment["issues"],
                retry_recommended=assessment["retry_recommended"],
                suggested_adjustment=assessment.get("suggested_adjustment", ""),
                validation_latency_ms=validation_latency_ms,
                error_type=None
            )

        return assessment

    except Exception as e:
        logger.error(f"Error during validation: {e}")

        # Calculate latency
        validation_latency_ms = int((time.time() - start_time) * 1000)

        # Check if it's a rate limit error
        error_str = str(e).lower()
        is_rate_limit = "rate limit" in error_str or "429" in error_str or "rate_limit_exceeded" in error_str

        if is_rate_limit:
            # Rate limit error - don't retry, return as valid
            logger.warning("Rate limit hit during validation - skipping validation and continuing")

            # Log to database
            if message_id:
                await _log_validation_result(
                    message_id=message_id,
                    is_valid=True,
                    confidence=0.5,
                    issues=["rate_limit_error"],
                    retry_recommended=False,
                    suggested_adjustment="",
                    validation_latency_ms=validation_latency_ms,
                    error_type="rate_limit"
                )

            return {
                "is_valid": True,
                "confidence": 0.5,
                "issues": ["rate_limit_error"],
                "retry_recommended": False,
                "suggested_adjustment": "",
                "error_type": "rate_limit",
                "validation_latency_ms": validation_latency_ms
            }

        # Other errors - assume valid if validation fails
        # Log to database
        if message_id:
            await _log_validation_result(
                message_id=message_id,
                is_valid=True,
                confidence=0.5,
                issues=["validation_error"],
                retry_recommended=False,
                suggested_adjustment="",
                validation_latency_ms=validation_latency_ms,
                error_type="validation_failure"
            )

        return {
            "is_valid": True,
            "confidence": 0.5,
            "issues": ["validation_error"],
            "retry_recommended": False,
            "suggested_adjustment": "",
            "error_type": "validation_failure",
            "validation_latency_ms": validation_latency_ms
        }


async def _log_validation_result(
    message_id: str,
    is_valid: bool,
    confidence: float,
    issues: List[str],
    retry_recommended: bool,
    suggested_adjustment: str,
    validation_latency_ms: int,
    error_type: Optional[str]
) -> None:
    """
    Log validation result to response_evaluations table

    Args:
        message_id: UUID of the message being validated
        is_valid: Whether the response passed validation
        confidence: Confidence score (0.0-1.0)
        issues: List of detected issues
        retry_recommended: Whether a retry is recommended
        suggested_adjustment: Suggested fix
        validation_latency_ms: Time taken for validation (ms)
        error_type: Error type if validation failed ('rate_limit', 'validation_failure', None)
    """
    try:
        client = get_supabase_client()

        # Insert validation result
        response = client.table("response_evaluations").insert({
            "message_id": message_id,
            "is_valid": is_valid,
            "confidence": confidence,
            "issues": issues,
            "retry_recommended": retry_recommended,
            "suggested_adjustment": suggested_adjustment or None,
            "validation_latency_ms": validation_latency_ms,
            "error_type": error_type
        }).execute()

        logger.info(f"Logged validation result for message {message_id[:8]}... (is_valid={is_valid}, confidence={confidence:.2f})")

    except Exception as e:
        # Don't fail the main flow if logging fails
        logger.error(f"Failed to log validation result to database: {e}")


async def log_validation_from_metadata(message_id: str, validation_metadata: Dict) -> None:
    """
    Log pre-computed validation result to database
    Used when validation was already performed but message_id wasn't available yet

    Args:
        message_id: UUID of the message being validated
        validation_metadata: Validation result dict from validate_response()
    """
    await _log_validation_result(
        message_id=message_id,
        is_valid=validation_metadata.get("is_valid", True),
        confidence=validation_metadata.get("confidence", 1.0),
        issues=validation_metadata.get("issues", []),
        retry_recommended=validation_metadata.get("retry_recommended", False),
        suggested_adjustment=validation_metadata.get("suggested_adjustment", ""),
        validation_latency_ms=validation_metadata.get("validation_latency_ms", 0),
        error_type=validation_metadata.get("error_type")
    )


def parse_validation_response(text: str) -> Dict:
    """
    Parse LLM validation response into structured format

    Expected format:
    ANSWERS_QUESTION: yes|no
    IS_GROUNDED: yes|no
    HAS_HALLUCINATION: yes|no
    IS_CONCISE: yes|no
    IS_PRECISE: yes|no
    CONFIDENCE: 0.0-1.0
    RETRY: yes|no
    ADJUSTMENT: suggested fix
    """
    import re

    lines = text.strip().split("\n")
    result = {
        "is_valid": True,
        "confidence": 1.0,
        "issues": [],
        "retry_recommended": False,
        "suggested_adjustment": ""
    }

    for line in lines:
        line = line.strip()

        if line.startswith("ANSWERS_QUESTION:"):
            answers = "yes" in line.lower()
            if not answers:
                result["is_valid"] = False
                result["issues"].append("doesn't answer question")

        elif line.startswith("IS_GROUNDED:"):
            grounded = "yes" in line.lower()
            if not grounded:
                result["is_valid"] = False
                result["issues"].append("not grounded in sources")

        elif line.startswith("HAS_HALLUCINATION:"):
            hallucination = "yes" in line.lower()
            if hallucination:
                result["is_valid"] = False
                result["issues"].append("hallucination detected")

        elif line.startswith("IS_CONCISE:"):
            concise = "yes" in line.lower()
            if not concise:
                result["is_valid"] = False
                result["issues"].append("response too verbose")

        elif line.startswith("IS_PRECISE:"):
            precise = "yes" in line.lower()
            if not precise:
                result["is_valid"] = False
                result["issues"].append("response lacks precision")

        elif line.startswith("CONFIDENCE:"):
            try:
                confidence_match = re.search(r"[\d.]+", line)
                if confidence_match:
                    confidence = float(confidence_match.group())
                    result["confidence"] = confidence
                    if confidence < 0.7:
                        result["is_valid"] = False
                        result["issues"].append("low confidence")
            except:
                pass

        elif line.startswith("RETRY:"):
            result["retry_recommended"] = "yes" in line.lower()

        elif line.startswith("ADJUSTMENT:"):
            result["suggested_adjustment"] = line.split(":", 1)[1].strip()

    return result


async def retry_with_adjustment(
    query: str,
    adjustment: str,
    original_threshold: float
) -> Dict:
    """
    Retry RAG pipeline with adjusted parameters

    Args:
        query: Original user query
        adjustment: Suggested adjustment from validation
        original_threshold: Original similarity threshold

    Returns:
        New RAG response with adjusted parameters
    """
    from app.services.rag_service import get_rag_response
    from app.core import config

    # Adjust threshold based on suggestion
    new_threshold = original_threshold
    new_top_k = 5

    adjustment_lower = adjustment.lower()

    if "lower threshold" in adjustment_lower or "expand search" in adjustment_lower:
        new_threshold = max(0.15, original_threshold - 0.1)
        logger.info(f"Retry: Lowering threshold from {original_threshold:.2f} to {new_threshold:.2f}")

    elif "more documents" in adjustment_lower or "increase top_k" in adjustment_lower:
        new_top_k = 10
        logger.info(f"Retry: Expanding search from top_k=5 to top_k={new_top_k}")

    elif "rephrase" in adjustment_lower:
        # For now, just lower threshold; future: could use LLM to rephrase query
        new_threshold = max(0.2, original_threshold - 0.05)
        logger.info(f"Retry: Adjusting threshold to {new_threshold:.2f} for rephrased search")

    # Override settings temporarily
    original_threshold_setting = config.settings.RAG_SIMILARITY_THRESHOLD
    original_top_k_setting = config.settings.RAG_TOP_K

    config.settings.RAG_SIMILARITY_THRESHOLD = new_threshold
    config.settings.RAG_TOP_K = new_top_k

    try:
        # Retry RAG
        response = await get_rag_response(query, include_history=False)

        return response
    finally:
        # Restore original settings
        config.settings.RAG_SIMILARITY_THRESHOLD = original_threshold_setting
        config.settings.RAG_TOP_K = original_top_k_setting
