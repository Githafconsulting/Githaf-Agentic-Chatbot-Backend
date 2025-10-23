"""
Chat API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from app.models.message import ChatRequest, ChatResponse
from app.services.rag_service import get_rag_response
from app.services.conversation_service import get_or_create_conversation, save_message
from app.middleware.rate_limiter import limiter
from app.utils.logger import get_logger
from app.utils.geolocation import get_country_from_ip, anonymize_ip
import uuid

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(chat_request: ChatRequest, request: Request):
    """
    Send a message and get AI response

    Rate limit: 10 requests per minute per IP
    """
    try:
        # Generate session ID if not provided
        session_id = chat_request.session_id or str(uuid.uuid4())

        # Get client IP address
        client_ip = request.client.host if request.client else None

        # Resolve IP to country (async operation)
        ip_address = None
        country_code = None
        country_name = None

        if client_ip:
            try:
                # Anonymize IP for GDPR compliance
                ip_address = anonymize_ip(client_ip)

                # Get country from IP
                geo_data = await get_country_from_ip(client_ip)
                country_code = geo_data.get("country_code")
                country_name = geo_data.get("country_name")

                logger.info(f"Request from {country_name or 'Unknown'} ({country_code or 'N/A'})")
            except Exception as e:
                logger.warning(f"Failed to resolve IP geolocation: {e}")

        # Get or create conversation with IP tracking
        conversation = await get_or_create_conversation(
            session_id=session_id,
            ip_address=ip_address,
            country_code=country_code,
            country_name=country_name
        )
        conversation_id = conversation["id"]

        # Save user message
        await save_message(
            conversation_id=conversation_id,
            role="user",
            content=chat_request.message
        )

        # Get RAG response
        rag_result = await get_rag_response(
            query=chat_request.message,
            session_id=session_id,
            include_history=True
        )

        response_text = rag_result["response"]
        sources = rag_result.get("sources", [])
        context_found = rag_result.get("context_found", len(sources) > 0)

        # Save assistant message
        message = await save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            context_used={"sources": sources} if sources else None
        )

        message_id = str(message["id"]) if message and "id" in message else None

        # Log validation result if available (Phase 1: Observation Layer)
        if message_id and "validation" in rag_result:
            try:
                from app.services.validation_service import log_validation_from_metadata
                await log_validation_from_metadata(message_id, rag_result["validation"])
                logger.info(f"Logged validation result for message {message_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to log validation result: {e}")

        # Extract semantic memory if conversation has enough messages (Phase 4: Advanced Memory)
        try:
            from app.services.rag_service import process_conversation_memory

            # Get message count from conversation
            message_count = conversation.get("message_count", 0) + 2  # +2 for current user + assistant messages

            # Only extract memory if conversation has 3+ meaningful exchanges
            if message_count >= 6:  # 3 user messages + 3 assistant messages
                logger.info(f"Extracting semantic memory for conversation {conversation_id[:8]}... ({message_count} messages)")
                memory_result = await process_conversation_memory(conversation_id, session_id)

                if memory_result.get("success") and memory_result.get("facts_stored", 0) > 0:
                    logger.info(f"Stored {memory_result['facts_stored']} semantic facts for session {session_id[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to extract semantic memory: {e}")

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            sources=sources if sources else None,
            context_found=context_found,
            message_id=message_id
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")
