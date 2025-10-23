"""
Chatbot Configuration Service
Manages chatbot settings including intents, confidence thresholds, and RAG parameters
"""
from typing import Dict, Any, Optional
from app.core.database import get_supabase_client
from app.utils.logger import get_logger
from app.services.intent_service import INTENT_PATTERNS, Intent
import json

logger = get_logger(__name__)


async def get_chatbot_config() -> Dict[str, Any]:
    """
    Get current chatbot configuration
    Auto-initializes database with actual patterns from intent_service.py if empty

    Returns:
        Dict: Chatbot configuration
    """
    try:
        client = get_supabase_client()

        # Get the first (and only) config record
        response = client.table("chatbot_config").select("*").limit(1).execute()

        if response.data and len(response.data) > 0:
            config = response.data[0]

            # Convert snake_case to camelCase for frontend
            return {
                "id": config.get("id"),
                "intentPatterns": config.get("intent_patterns", {}),
                "intentEnabled": config.get("intent_enabled", {}),
                "patternConfidenceThreshold": config.get("pattern_confidence_threshold", 0.7),
                "llmFallbackEnabled": config.get("llm_fallback_enabled", True),
                "llmConfidenceThreshold": config.get("llm_confidence_threshold", 0.6),
                "ragTopK": config.get("rag_top_k", 5),
                "ragSimilarityThreshold": config.get("rag_similarity_threshold", 0.5),
                "chunkSize": config.get("chunk_size", 500),
                "chunkOverlap": config.get("chunk_overlap", 50),
                "llmModel": config.get("llm_model", "llama-3.1-8b-instant"),
                "llmTemperature": config.get("llm_temperature", 0.7),
                "llmMaxTokens": config.get("llm_max_tokens", 500),
                "topicKeywords": config.get("topic_keywords", {}),
                "createdAt": config.get("created_at"),
                "updatedAt": config.get("updated_at")
            }

        # No config exists - initialize database with actual patterns from intent_service.py
        logger.info("No chatbot config found, initializing with patterns from intent_service.py")
        default_db_config = _get_default_config_for_db()
        client.table("chatbot_config").insert(default_db_config).execute()
        logger.info("Initialized chatbot config with 70 intent patterns")

        # Return the newly created config
        return await get_chatbot_config()

    except Exception as e:
        logger.error(f"Error getting chatbot config: {e}")
        return _get_default_config()


async def update_chatbot_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update chatbot configuration

    Args:
        updates: Dictionary of fields to update

    Returns:
        Dict: Updated configuration
    """
    try:
        client = get_supabase_client()

        # Convert camelCase keys to snake_case for database
        db_updates = {}
        key_mapping = {
            "intentPatterns": "intent_patterns",
            "intentEnabled": "intent_enabled",
            "patternConfidenceThreshold": "pattern_confidence_threshold",
            "llmFallbackEnabled": "llm_fallback_enabled",
            "llmConfidenceThreshold": "llm_confidence_threshold",
            "ragTopK": "rag_top_k",
            "ragSimilarityThreshold": "rag_similarity_threshold",
            "chunkSize": "chunk_size",
            "chunkOverlap": "chunk_overlap",
            "llmModel": "llm_model",
            "llmTemperature": "llm_temperature",
            "llmMaxTokens": "llm_max_tokens",
            "topicKeywords": "topic_keywords"
        }

        for camel_key, value in updates.items():
            if camel_key in key_mapping:
                db_updates[key_mapping[camel_key]] = value

        # Get existing config ID
        existing = client.table("chatbot_config").select("id").limit(1).execute()

        if existing.data and len(existing.data) > 0:
            config_id = existing.data[0]["id"]

            # Update existing config
            response = client.table("chatbot_config").update(db_updates).eq(
                "id", config_id
            ).execute()

            logger.info(f"Updated chatbot config: {list(db_updates.keys())}")
        else:
            # Create new config if none exists
            response = client.table("chatbot_config").insert(db_updates).execute()
            logger.info("Created new chatbot config")

        # Return updated config
        return await get_chatbot_config()

    except Exception as e:
        logger.error(f"Error updating chatbot config: {e}")
        raise


async def reset_chatbot_config() -> Dict[str, Any]:
    """
    Reset chatbot configuration to defaults

    Returns:
        Dict: Default configuration
    """
    try:
        client = get_supabase_client()

        # Get existing config ID
        existing = client.table("chatbot_config").select("id").limit(1).execute()

        default_config = _get_default_config_for_db()

        if existing.data and len(existing.data) > 0:
            config_id = existing.data[0]["id"]

            # Update to defaults
            client.table("chatbot_config").update(default_config).eq(
                "id", config_id
            ).execute()

            logger.info("Reset chatbot config to defaults")
        else:
            # Insert defaults
            client.table("chatbot_config").insert(default_config).execute()
            logger.info("Created default chatbot config")

        return await get_chatbot_config()

    except Exception as e:
        logger.error(f"Error resetting chatbot config: {e}")
        raise


def _get_default_config() -> Dict[str, Any]:
    """Get default configuration in camelCase format using actual intent patterns"""
    # Convert INTENT_PATTERNS from intent_service.py to dict with string keys
    intent_patterns_dict = {}
    intent_enabled_dict = {}

    for intent_enum, patterns in INTENT_PATTERNS.items():
        intent_key = intent_enum.value  # Convert Intent enum to string (e.g., "greeting")
        intent_patterns_dict[intent_key] = patterns
        intent_enabled_dict[intent_key] = True

    # Also enable out_of_scope (not in INTENT_PATTERNS but exists as intent)
    intent_enabled_dict["out_of_scope"] = True

    return {
        "id": None,
        "intentPatterns": intent_patterns_dict,
        "intentEnabled": intent_enabled_dict,
        "patternConfidenceThreshold": 0.7,
        "llmFallbackEnabled": True,
        "llmConfidenceThreshold": 0.6,
        "ragTopK": 5,
        "ragSimilarityThreshold": 0.5,
        "chunkSize": 500,
        "chunkOverlap": 50,
        "llmModel": "llama-3.1-8b-instant",
        "llmTemperature": 0.7,
        "llmMaxTokens": 500,
        "topicKeywords": {
            "services": ["service", "services", "offer", "provide", "do you do", "specialize", "expertise"],
            "pricing": ["price", "pricing", "cost", "costs", "how much", "expensive", "rate", "rates", "fee", "fees", "payment"],
            "contact": ["contact", "email", "phone", "call", "reach", "address", "location", "office", "where"],
            "hours": ["hours", "open", "available", "availability", "schedule", "when", "time"],
            "process": ["process", "how do", "how does", "work", "steps", "procedure", "workflow"],
            "technology": ["technology", "technologies", "tech", "tools", "framework", "platform", "stack"],
            "support": ["support", "help", "assist", "problem", "issue", "trouble", "fix"],
            "team": ["team", "who", "employees", "staff", "people", "experience", "experts"],
            "projects": ["project", "projects", "portfolio", "work", "clients", "case study", "examples"]
        },
        "createdAt": None,
        "updatedAt": None
    }


def _get_default_config_for_db() -> Dict[str, Any]:
    """Get default configuration in snake_case format for database"""
    config = _get_default_config()
    return {
        "intent_patterns": config["intentPatterns"],
        "intent_enabled": config["intentEnabled"],
        "pattern_confidence_threshold": config["patternConfidenceThreshold"],
        "llm_fallback_enabled": config["llmFallbackEnabled"],
        "llm_confidence_threshold": config["llmConfidenceThreshold"],
        "rag_top_k": config["ragTopK"],
        "rag_similarity_threshold": config["ragSimilarityThreshold"],
        "chunk_size": config["chunkSize"],
        "chunk_overlap": config["chunkOverlap"],
        "llm_model": config["llmModel"],
        "llm_temperature": config["llmTemperature"],
        "llm_max_tokens": config["llmMaxTokens"],
        "topic_keywords": config["topicKeywords"]
    }
