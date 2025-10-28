"""
Chatbot model for multi-tenant support
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class ChatbotBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    greeting_message: str = Field(default="Hi! How can I help you today?", max_length=200)

    # Branding (optional - uses company defaults if not set)
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    logo_url: Optional[str] = None

    # Configuration
    model_preset: str = Field(default="balanced", pattern=r'^(fast|balanced|accurate)$')
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=500, ge=100, le=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # Access Control
    allowed_domains: List[str] = Field(default_factory=list)
    rate_limit_per_ip: int = Field(default=10, ge=1, le=100)


class ChatbotCreate(ChatbotBase):
    """Schema for creating a new chatbot"""
    company_id: str  # Will be set from JWT context


class ChatbotUpdate(BaseModel):
    """Schema for updating chatbot settings"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    greeting_message: Optional[str] = Field(None, max_length=200)
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    logo_url: Optional[str] = None
    model_preset: Optional[str] = Field(None, pattern=r'^(fast|balanced|accurate)$')
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=2000)
    top_k: Optional[int] = Field(None, ge=1, le=20)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    allowed_domains: Optional[List[str]] = None
    rate_limit_per_ip: Optional[int] = Field(None, ge=1, le=100)


class Chatbot(ChatbotBase):
    """Chatbot model with database fields"""
    id: str
    company_id: str
    is_active: bool = True
    deploy_status: str = "draft"  # draft, deployed, paused

    # Metrics
    total_conversations: int = 0
    total_messages: int = 0
    avg_satisfaction: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatbotWithEmbedCode(Chatbot):
    """Chatbot with generated embed code"""
    embed_code: str


class ChatbotDeploy(BaseModel):
    """Schema for deploying/pausing a chatbot"""
    deploy_status: str = Field(..., pattern=r'^(deployed|paused)$')


class ChatbotStats(BaseModel):
    """Detailed chatbot statistics"""
    total_conversations: int
    total_messages: int
    avg_satisfaction: Optional[float]
    avg_response_time: Optional[float]
    satisfaction_rate: Optional[float]
    response_rate: Optional[float]
    top_queries: List[dict]
    daily_stats: List[dict]
