"""
System Settings API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.settings import SystemSettings
from app.services import settings_service
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=SystemSettings)
async def get_settings(current_user=Depends(get_current_user)):
    """
    Get system settings

    Requires authentication
    """
    try:
        settings = await settings_service.get_settings()
        return settings

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=SystemSettings)
async def update_settings(
    settings: SystemSettings,
    current_user=Depends(get_current_user)
):
    """
    Update system settings

    Requires authentication
    """
    try:
        # Validate at least one language is enabled
        if not settings.enabled_languages or len(settings.enabled_languages) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one language must be enabled"
            )

        # Validate default language is in enabled languages
        if settings.default_language not in settings.enabled_languages:
            raise HTTPException(
                status_code=400,
                detail="Default language must be one of the enabled languages"
            )

        updated_settings = await settings_service.update_settings(settings)
        logger.info(f"Settings updated by user: {current_user['id']}")
        return updated_settings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=SystemSettings)
async def reset_settings(current_user=Depends(get_current_user)):
    """
    Reset settings to defaults

    Requires authentication
    """
    try:
        settings = await settings_service.reset_settings()
        logger.info(f"Settings reset by user: {current_user['id']}")
        return settings

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
