"""
Feedback-related Pydantic models
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class Feedback(BaseModel):
    """Feedback database model"""
    id: UUID
    message_id: UUID
    rating: int = Field(..., ge=0, le=1, description="Rating: 0=thumbs down, 1=thumbs up")
    comment: Optional[str] = None
    created_at: datetime


class FeedbackCreate(BaseModel):
    """Model for creating feedback"""
    message_id: UUID
    rating: int = Field(..., ge=0, le=1, description="Rating: 0=thumbs down, 1=thumbs up")
    comment: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    success: bool
    message: str
