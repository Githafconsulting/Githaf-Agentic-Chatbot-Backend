"""
Widget Settings Service
Manages widget customization settings
"""
from typing import Dict, Optional
from app.core.database import get_supabase_client
from app.models.widget import WidgetSettings, WidgetSettingsUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_widget_settings() -> Optional[Dict]:
    """
    Get current widget settings

    Returns:
        Dict with widget settings or None if not found
    """
    try:
        client = get_supabase_client()

        # Get the most recent settings (should only be one row)
        response = client.table("widget_settings").select("*").order("updated_at", desc=True).limit(1).execute()

        if response.data and len(response.data) > 0:
            # Parse through Pydantic model to convert snake_case to camelCase
            raw_settings = response.data[0]
            widget_settings = WidgetSettings(**raw_settings)
            # Serialize with mode='json' to properly convert datetime to strings
            serialized = widget_settings.model_dump(by_alias=False, exclude_none=True, mode='json')
            logger.info("Retrieved widget settings successfully")
            return serialized
        else:
            logger.warning("No widget settings found, returning defaults")
            return _get_default_settings()

    except Exception as e:
        logger.error(f"Error retrieving widget settings: {e}")
        return _get_default_settings()


async def update_widget_settings(settings_update: WidgetSettingsUpdate) -> Dict:
    """
    Update widget settings

    Args:
        settings_update: Partial or full settings update

    Returns:
        Updated settings dict
    """
    try:
        client = get_supabase_client()

        # Get current settings to update
        current = client.table("widget_settings").select("*").order("updated_at", desc=True).limit(1).execute()

        # Prepare update data - include all fields sent from frontend
        # Use by_alias=True to convert camelCase to snake_case
        update_data = settings_update.model_dump(by_alias=True, exclude_none=True, exclude_unset=False)

        # Remove None values but keep False/0/empty string values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            logger.warning("No fields to update")
            return await get_widget_settings()

        logger.info("Updating widget settings")

        if current.data and len(current.data) > 0:
            # Update existing settings
            settings_id = current.data[0]["id"]
            response = client.table("widget_settings").update(update_data).eq("id", settings_id).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Successfully updated widget settings ID: {settings_id}")
                # Parse through Pydantic model to return camelCase
                raw_settings = response.data[0]
                widget_settings = WidgetSettings(**raw_settings)
                return widget_settings.model_dump(by_alias=False, exclude_none=True, mode='json')
            else:
                logger.error(f"Update response had no data: {response}")
                return await get_widget_settings()
        else:
            # Insert new settings if none exist
            response = client.table("widget_settings").insert(update_data).execute()
            logger.info("Created new widget settings")
            if response.data:
                raw_settings = response.data[0]
                widget_settings = WidgetSettings(**raw_settings)
                return widget_settings.model_dump(by_alias=False, exclude_none=True, mode='json')
            else:
                return await get_widget_settings()

    except Exception as e:
        logger.error(f"Error updating widget settings: {e}")
        raise


async def reset_widget_settings() -> Dict:
    """
    Reset widget settings to defaults

    Returns:
        Default settings dict
    """
    try:
        client = get_supabase_client()

        # Get current settings
        current = client.table("widget_settings").select("*").order("updated_at", desc=True).limit(1).execute()

        # Get defaults in both formats
        defaults_for_db = _get_default_settings_db()  # snake_case for database
        defaults_for_frontend = _get_default_settings()  # camelCase for frontend

        if current.data and len(current.data) > 0:
            # Update to defaults (use snake_case for database)
            settings_id = current.data[0]["id"]
            response = client.table("widget_settings").update(defaults_for_db).eq("id", settings_id).execute()
            logger.info("Reset widget settings to defaults")
            if response.data:
                raw_settings = response.data[0]
                widget_settings = WidgetSettings(**raw_settings)
                return widget_settings.model_dump(by_alias=False, exclude_none=True, mode='json')
            return defaults_for_frontend
        else:
            # Insert defaults (use snake_case for database)
            response = client.table("widget_settings").insert(defaults_for_db).execute()
            logger.info("Created default widget settings")
            if response.data:
                raw_settings = response.data[0]
                widget_settings = WidgetSettings(**raw_settings)
                return widget_settings.model_dump(by_alias=False, exclude_none=True, mode='json')
            return defaults_for_frontend

    except Exception as e:
        logger.error(f"Error resetting widget settings: {e}")
        raise


def _get_default_widget_model() -> WidgetSettings:
    """Create default widget settings model"""
    return WidgetSettings(
        widgetTheme="modern",
        primaryColor="#1e40af",
        accentColor="#0ea5e9",
        buttonSize="medium",
        showNotificationBadge=True,
        widgetPosition="bottom-right",
        horizontalPadding=20,
        verticalPadding=20,
        zIndex=1000,
        widgetTitle="Githaf AI Assistant",
        widgetSubtitle="Always here to help",
        greetingMessage="Hi! How can I help you today?",
        apiUrl="/api/v1/chat/"
    )


def _get_default_settings() -> Dict:
    """Get default widget settings (camelCase for frontend)"""
    return _get_default_widget_model().model_dump(by_alias=False, exclude_none=True, mode='json')


def _get_default_settings_db() -> Dict:
    """Get default widget settings (snake_case for database)"""
    return _get_default_widget_model().model_dump(by_alias=True, exclude_none=True, mode='json')
