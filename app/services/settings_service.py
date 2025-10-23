"""
System Settings Service
"""
from typing import Optional
from app.core.database import get_supabase_client
from app.models.settings import SystemSettings
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def get_settings() -> Optional[SystemSettings]:
    """
    Get system settings

    Returns:
        SystemSettings or None if not found
    """
    try:
        client = get_supabase_client()

        # Get the first (and only) settings record
        response = client.table("system_settings").select("*").limit(1).execute()

        if not response.data or len(response.data) == 0:
            # Return default settings if none exist
            logger.info("No settings found, returning defaults")
            return SystemSettings()

        settings_data = response.data[0]

        # Convert database record to SystemSettings model
        return SystemSettings(
            default_theme=settings_data.get("default_theme", "dark"),
            allow_theme_switching=settings_data.get("allow_theme_switching", True),
            inherit_host_theme=settings_data.get("inherit_host_theme", True),
            default_language=settings_data.get("default_language", "en"),
            enabled_languages=settings_data.get("enabled_languages", ["en", "fr", "de", "es", "ar"]),
            translate_ai_responses=settings_data.get("translate_ai_responses", True),
            enable_rtl=settings_data.get("enable_rtl", True),
            enable_country_tracking=settings_data.get("enable_country_tracking", True),
            default_date_range=settings_data.get("default_date_range", "30d"),
            enable_world_map=settings_data.get("enable_world_map", True),
            anonymize_ips=settings_data.get("anonymize_ips", True),
            store_ip_addresses=settings_data.get("store_ip_addresses", False)
        )

    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        # Return defaults on error
        return SystemSettings()


async def update_settings(settings: SystemSettings) -> SystemSettings:
    """
    Update or create system settings

    Args:
        settings: SystemSettings model

    Returns:
        Updated SystemSettings
    """
    try:
        client = get_supabase_client()

        # Check if settings exist
        existing = client.table("system_settings").select("id").limit(1).execute()

        settings_dict = settings.model_dump()
        settings_dict["updated_at"] = datetime.utcnow().isoformat()

        if existing.data and len(existing.data) > 0:
            # Update existing settings
            settings_id = existing.data[0]["id"]
            response = client.table("system_settings").update(settings_dict).eq("id", settings_id).execute()
            logger.info(f"Updated settings with ID: {settings_id}")
        else:
            # Insert new settings
            response = client.table("system_settings").insert(settings_dict).execute()
            logger.info("Created new settings record")

        return settings

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise


async def reset_settings() -> SystemSettings:
    """
    Reset settings to defaults

    Returns:
        Default SystemSettings
    """
    try:
        default_settings = SystemSettings()
        return await update_settings(default_settings)

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise
