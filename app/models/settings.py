"""
System Settings models
"""
from pydantic import BaseModel, Field
from typing import List, Optional


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class SystemSettings(BaseModel):
    """System-wide configuration settings"""
    # Theme Settings
    default_theme: str = Field(default="dark", alias="defaultTheme")
    allow_theme_switching: bool = Field(default=True, alias="allowThemeSwitching")
    inherit_host_theme: bool = Field(default=True, alias="inheritHostTheme")

    # Language Settings
    default_language: str = Field(default="en", alias="defaultLanguage")
    enabled_languages: List[str] = Field(default=["en", "fr", "de", "es", "ar"], alias="enabledLanguages")
    translate_ai_responses: bool = Field(default=True, alias="translateAIResponses")
    enable_rtl: bool = Field(default=True, alias="enableRTL")

    # Analytics Settings
    enable_country_tracking: bool = Field(default=True, alias="enableCountryTracking")
    default_date_range: str = Field(default="30d", alias="defaultDateRange")
    enable_world_map: bool = Field(default=True, alias="enableWorldMap")

    # Privacy Settings
    anonymize_ips: bool = Field(default=True, alias="anonymizeIPs")
    store_ip_addresses: bool = Field(default=False, alias="storeIPAddresses")

    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase
        alias_generator = to_camel  # Auto-convert to camelCase for JSON
        json_schema_extra = {
            "example": {
                "defaultTheme": "dark",
                "allowThemeSwitching": True,
                "inheritHostTheme": True,
                "defaultLanguage": "en",
                "enabledLanguages": ["en", "fr", "de", "es", "ar"],
                "translateAIResponses": True,
                "enableRTL": True,
                "enableCountryTracking": True,
                "defaultDateRange": "30d",
                "enableWorldMap": True,
                "anonymizeIPs": True,
                "storeIPAddresses": False
            }
        }


class SystemSettingsResponse(SystemSettings):
    """Response model with additional metadata"""
    id: str
    updated_at: str
