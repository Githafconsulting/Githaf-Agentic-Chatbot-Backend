"""
LLM service using Groq API
"""
from typing import Optional, AsyncGenerator
from groq import Groq
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Groq client singleton
_client: Groq = None


def get_groq_client() -> Groq:
    """
    Get or create Groq client

    Returns:
        Groq: Groq client instance
    """
    global _client

    if _client is None:
        logger.info("Initializing Groq client")
        # Add longer timeout to handle slow DNS resolution on Windows
        _client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=60.0,  # Increased timeout for Windows DNS issues
            max_retries=3
        )

    return _client


async def generate_response(
    prompt: str,
    system_message: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Generate response from LLM

    Args:
        prompt: User prompt
        system_message: Optional system message
        temperature: Sampling temperature (default from settings)
        max_tokens: Maximum tokens (default from settings)

    Returns:
        str: Generated response
    """
    try:
        client = get_groq_client()

        # Build messages
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        # Set defaults
        if temperature is None:
            temperature = settings.LLM_TEMPERATURE

        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS

        logger.info(f"Calling Groq API with model: {settings.LLM_MODEL}")

        # Call API
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract response
        generated_text = response.choices[0].message.content

        logger.info(f"Generated response ({len(generated_text)} characters)")

        return generated_text

    except Exception as e:
        error_str = str(e)

        # Check if it's a rate limit error
        if "rate limit" in error_str.lower() or "429" in error_str or "rate_limit_exceeded" in error_str.lower():
            logger.error(f"Rate limit error - Groq API quota exceeded. Wait a few minutes or upgrade plan.")
            logger.error(f"Error: {e}")
        else:
            logger.error(f"Error calling Groq API: {e}")

        raise


async def generate_response_stream(
    prompt: str,
    system_message: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response from LLM

    Args:
        prompt: User prompt
        system_message: Optional system message
        temperature: Sampling temperature
        max_tokens: Maximum tokens

    Yields:
        str: Response chunks
    """
    try:
        client = get_groq_client()

        # Build messages
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        # Set defaults
        if temperature is None:
            temperature = settings.LLM_TEMPERATURE

        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS

        logger.info(f"Calling Groq API (streaming) with model: {settings.LLM_MODEL}")

        # Call API with streaming
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        # Yield chunks
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"Error in streaming response: {e}")
        raise
