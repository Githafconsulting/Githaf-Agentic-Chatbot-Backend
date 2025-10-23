"""
Pydantic models for soft delete operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SoftDeleteRequest(BaseModel):
    """Request model for soft delete operations"""
    item_id: UUID = Field(..., description="UUID of item to delete")


class RecoverRequest(BaseModel):
    """Request model for recovery operations"""
    item_id: UUID = Field(..., description="UUID of item to recover")


class PermanentDeleteRequest(BaseModel):
    """Request model for permanent delete operations"""
    item_id: UUID = Field(..., description="UUID of item to permanently delete")
    confirm: bool = Field(..., description="Confirmation flag (must be true)")


class UpdateConversationRequest(BaseModel):
    """Request model for updating conversation"""
    session_id: Optional[str] = Field(None, description="New session ID")


class UpdateMessageRequest(BaseModel):
    """Request model for updating message"""
    content: str = Field(..., min_length=1, max_length=5000, description="New message content")


class UpdateFeedbackRequest(BaseModel):
    """Request model for updating feedback"""
    rating: Optional[int] = Field(None, ge=0, le=1, description="New rating (0 or 1)")
    comment: Optional[str] = Field(None, max_length=2000, description="New comment")


class DeletedItem(BaseModel):
    """Model for deleted item data"""
    item_type: str = Field(..., description="Type: conversation, message, or feedback")
    id: UUID = Field(..., description="Item UUID")
    identifier: str = Field(..., description="Session ID or related ID")
    content: Optional[str] = Field(None, description="Content if applicable")
    deleted_at: datetime = Field(..., description="Deletion timestamp")
    deleted_by: Optional[UUID] = Field(None, description="User who deleted")
    created_at: datetime = Field(..., description="Original creation timestamp")
    deleted_by_email: Optional[str] = Field(None, description="Email of user who deleted")
    related_count: int = Field(0, description="Count of related items")
    days_until_permanent: int = Field(0, description="Days remaining until permanent deletion")

    class Config:
        from_attributes = True


class DeletedItemsResponse(BaseModel):
    """Response model for list of deleted items"""
    items: List[DeletedItem] = Field(default_factory=list)
    total: int = Field(0, description="Total count of deleted items")
    limit: int = Field(100, description="Items per page")
    offset: int = Field(0, description="Pagination offset")


class SoftDeleteResponse(BaseModel):
    """Response model for soft delete operations"""
    success: bool
    message: str
    item_id: str


class RecoverResponse(BaseModel):
    """Response model for recovery operations"""
    success: bool
    message: str
    item_id: str


class PermanentDeleteResponse(BaseModel):
    """Response model for permanent delete operations"""
    success: bool
    message: str
    item_id: str


class UpdateResponse(BaseModel):
    """Generic response model for update operations"""
    success: bool
    message: str
    data: Optional[dict] = None


class CleanupResponse(BaseModel):
    """Response model for cleanup operation"""
    success: bool
    message: str
    deleted_count: int
