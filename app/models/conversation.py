"""
Conversation-related Pydantic models
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from app.models.message import Message


class Conversation(BaseModel):
    """Conversation database model"""
    id: UUID
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime
    last_message_at: Optional[datetime] = None


class ConversationCreate(BaseModel):
    """Model for creating a new conversation"""
    session_id: str = Field(..., min_length=1, max_length=255)


class ConversationDetail(BaseModel):
    """Detailed conversation with messages"""
    id: UUID
    session_id: str
    created_at: datetime
    last_message_at: Optional[datetime]
    messages: List[Message] = []


class ConversationList(BaseModel):
    """List of conversations"""
    conversations: List[Conversation]
    total: int
