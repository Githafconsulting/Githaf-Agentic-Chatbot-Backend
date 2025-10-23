"""
Chatbot Configuration API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.chatbot_config import ChatbotConfig, ChatbotConfigUpdate
from app.services.chatbot_config_service import (
    get_chatbot_config,
    update_chatbot_config,
    reset_chatbot_config
)
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def get_config(current_user: dict = Depends(get_current_user)):
    """
    Get current chatbot configuration

    Requires authentication
    Returns config with camelCase field names (not snake_case aliases)
    """
    try:
        config = await get_chatbot_config()
        logger.info(f"Returning chatbot config with {len(config.get('intentPatterns', {}))} intent types")
        return config  # Already in camelCase from service

    except Exception as e:
        logger.error(f"Error getting chatbot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/")
async def update_config(
    updates: ChatbotConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update chatbot configuration

    Requires authentication
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = updates.model_dump(exclude_none=True)

        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        updated_config = await update_chatbot_config(update_dict)

        return {
            "success": True,
            "message": "Chatbot configuration updated successfully",
            "config": updated_config
        }

    except Exception as e:
        logger.error(f"Error updating chatbot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_config(current_user: dict = Depends(get_current_user)):
    """
    Reset chatbot configuration to defaults

    Requires authentication
    """
    try:
        default_config = await reset_chatbot_config()

        return {
            "success": True,
            "message": "Chatbot configuration reset to defaults",
            "config": default_config
        }

    except Exception as e:
        logger.error(f"Error resetting chatbot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
