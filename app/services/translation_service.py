"""
Translation Service
Translates AI responses to different languages
Uses LibreTranslate API (open-source, self-hostable)
"""
import httpx
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Language code mapping
LANGUAGE_CODES = {
    "en": "en",  # English
    "fr": "fr",  # French
    "de": "de",  # German
    "es": "es",  # Spanish
    "ar": "ar",  # Arabic
}

# LibreTranslate public instance (or self-hosted)
LIBRETRANSLATE_URL = "https://libretranslate.com/translate"


async def translate_text(text: str, target_language: str, source_language: str = "en") -> Optional[str]:
    """
    Translate text to target language using LibreTranslate API
    
    Args:
        text: Text to translate
        target_language: Target language code (en, fr, de, es, ar)
        source_language: Source language code (default: en)
    
    Returns:
        Translated text or None if translation fails
    """
    # Skip if target is same as source
    if target_language == source_language:
        return text
    
    # Skip if target language not supported
    if target_language not in LANGUAGE_CODES:
        logger.warning(f"Unsupported target language: {target_language}")
        return text
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                LIBRETRANSLATE_URL,
                json={
                    "q": text,
                    "source": source_language,
                    "target": target_language,
                    "format": "text"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                translated_text = data.get("translatedText", text)
                logger.info(f"Translated text from {source_language} to {target_language}")
                return translated_text
            else:
                logger.error(f"Translation API error: {response.status_code}")
                return text
                
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text


async def should_translate_response(session_id: Optional[str] = None) -> bool:
    """
    Check if AI responses should be translated based on system settings
    
    Args:
        session_id: Optional session ID
    
    Returns:
        Boolean indicating if translation is enabled
    """
    try:
        from app.services.settings_service import get_settings
        settings = await get_settings()
        return settings.get("translate_ai_responses", False)
    except Exception as e:
        logger.error(f"Error checking translation settings: {e}")
        return False


async def get_user_language(session_id: Optional[str] = None) -> str:
    """
    Get user's preferred language
    
    Args:
        session_id: Optional session ID
    
    Returns:
        Language code (default: en)
    """
    # TODO: Implement user language preference storage
    # For now, return default from system settings
    try:
        from app.services.settings_service import get_settings
        settings = await get_settings()
        return settings.get("default_language", "en")
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return "en"


async def translate_ai_response(
    response_text: str,
    session_id: Optional[str] = None,
    target_language: Optional[str] = None
) -> str:
    """
    Translate AI response if translation is enabled
    
    Args:
        response_text: Original AI response in English
        session_id: Optional session ID
        target_language: Optional override for target language
    
    Returns:
        Translated text (or original if translation disabled/fails)
    """
    # Check if translation is enabled
    if not await should_translate_response(session_id):
        return response_text
    
    # Get target language
    if target_language is None:
        target_language = await get_user_language(session_id)
    
    # Skip if English (original language)
    if target_language == "en":
        return response_text
    
    # Translate
    translated = await translate_text(response_text, target_language, source_language="en")
    return translated or response_text
