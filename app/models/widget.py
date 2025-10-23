"""
Widget Settings Models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WidgetSettingsBase(BaseModel):
    """Base widget settings schema"""
    # Appearance
    widgetTheme: str = Field(default="modern", alias="widget_theme")
    primaryColor: str = Field(default="#1e40af", alias="primary_color")
    accentColor: str = Field(default="#0ea5e9", alias="accent_color")
    buttonSize: str = Field(default="medium", alias="button_size")
    showNotificationBadge: bool = Field(default=True, alias="show_notification_badge")

    # Position
    widgetPosition: str = Field(default="bottom-right", alias="widget_position")
    horizontalPadding: int = Field(default=20, alias="horizontal_padding")
    verticalPadding: int = Field(default=20, alias="vertical_padding")
    zIndex: int = Field(default=1000, alias="z_index")

    # Content
    widgetTitle: str = Field(default="Githaf AI Assistant", alias="widget_title")
    widgetSubtitle: str = Field(default="Always here to help", alias="widget_subtitle")
    greetingMessage: str = Field(default="Hi! How can I help you today?", alias="greeting_message")
    apiUrl: str = Field(default="/api/v1/chat/", alias="api_url")

    model_config = {
        "populate_by_name": True,  # Allow both camelCase and snake_case
    }


class WidgetSettings(WidgetSettingsBase):
    """Full widget settings with metadata"""
    id: Optional[str] = None
    createdAt: Optional[datetime] = Field(default=None, alias="created_at")
    updatedAt: Optional[datetime] = Field(default=None, alias="updated_at")


class WidgetSettingsUpdate(BaseModel):
    """Schema for updating widget settings"""
    # Appearance (all optional)
    widgetTheme: Optional[str] = Field(default=None, alias="widget_theme")
    primaryColor: Optional[str] = Field(default=None, alias="primary_color")
    accentColor: Optional[str] = Field(default=None, alias="accent_color")
    buttonSize: Optional[str] = Field(default=None, alias="button_size")
    showNotificationBadge: Optional[bool] = Field(default=None, alias="show_notification_badge")

    # Position (all optional)
    widgetPosition: Optional[str] = Field(default=None, alias="widget_position")
    horizontalPadding: Optional[int] = Field(default=None, alias="horizontal_padding")
    verticalPadding: Optional[int] = Field(default=None, alias="vertical_padding")
    zIndex: Optional[int] = Field(default=None, alias="z_index")

    # Content (all optional)
    widgetTitle: Optional[str] = Field(default=None, alias="widget_title")
    widgetSubtitle: Optional[str] = Field(default=None, alias="widget_subtitle")
    greetingMessage: Optional[str] = Field(default=None, alias="greeting_message")
    apiUrl: Optional[str] = Field(default=None, alias="api_url")

    model_config = {
        "populate_by_name": True,
    }
