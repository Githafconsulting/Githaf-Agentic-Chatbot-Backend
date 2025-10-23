"""
Message and chat-related Pydantic models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Retrieved document sources")
    context_found: bool = Field(True, description="Whether relevant context was found")
    message_id: Optional[str] = Field(None, description="Message ID for feedback tracking")


class Message(BaseModel):
    """Message database model"""
    id: UUID
    conversation_id: UUID
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    context_used: Optional[Dict[str, Any]] = None
    created_at: datetime


class MessageCreate(BaseModel):
    """Model for creating a new message"""
    conversation_id: UUID
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    context_used: Optional[Dict[str, Any]] = None
