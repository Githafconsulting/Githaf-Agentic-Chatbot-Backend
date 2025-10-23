"""
Draft Document Pydantic Models
For semi-automated knowledge base learning system
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class DraftDocumentBase(BaseModel):
    """Base draft document schema"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    query_pattern: Optional[str] = Field(None, max_length=200)


class DraftDocumentCreate(DraftDocumentBase):
    """Schema for creating a draft document"""
    source_type: str = Field(default="feedback_generated")
    source_feedback_ids: Optional[List[UUID]] = None
    generated_by_llm: bool = True
    llm_model: Optional[str] = None
    generation_prompt: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class DraftDocumentUpdate(BaseModel):
    """Schema for updating a draft document"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected|needs_revision)$")
    review_notes: Optional[str] = None


class DraftDocumentReview(BaseModel):
    """Schema for reviewing a draft document"""
    status: str = Field(..., pattern="^(approved|rejected|needs_revision)$")
    review_notes: Optional[str] = Field(None, max_length=1000)


class DraftDocument(DraftDocumentBase):
    """Complete draft document schema"""
    id: UUID
    source_type: str
    source_feedback_ids: Optional[List[UUID]] = None
    query_pattern: Optional[str] = None

    generated_by_llm: bool
    llm_model: Optional[str] = None
    generation_prompt: Optional[str] = None
    confidence_score: Optional[float] = None

    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    published_document_id: Optional[UUID] = None
    published_at: Optional[datetime] = None

    view_count: int
    feedback_count: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackInsight(BaseModel):
    """Aggregated feedback pattern identifying knowledge gaps"""
    id: UUID
    query_pattern: str
    pattern_keywords: List[str]

    total_feedback_count: int
    negative_feedback_count: int
    positive_feedback_count: int
    avg_rating: float

    sample_queries: List[str]
    sample_feedback_ids: List[UUID]

    status: str
    priority: str

    draft_document_id: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackInsightSummary(BaseModel):
    """Summary of feedback insights for dashboard"""
    total_patterns: int
    critical_issues: int
    high_priority: int
    medium_priority: int
    low_priority: int
    resolved_this_week: int
    pending_drafts: int
    top_issues: List[FeedbackInsight]


class LearningMetrics(BaseModel):
    """Daily metrics for learning system effectiveness"""
    id: UUID
    metric_date: datetime

    total_feedback: int
    negative_feedback: int
    feedback_with_comments: int

    drafts_generated: int
    drafts_approved: int
    drafts_rejected: int
    approval_rate: Optional[float] = None

    documents_added_from_feedback: int
    avg_time_to_resolution_hours: Optional[float] = None

    queries_resolved: int
    satisfaction_improvement: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateDraftRequest(BaseModel):
    """Request to generate a draft from feedback"""
    feedback_ids: List[UUID] = Field(..., min_items=1, max_items=10)
    query_pattern: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    additional_context: Optional[str] = Field(None, max_length=1000)


class GenerateDraftResponse(BaseModel):
    """Response after generating a draft"""
    success: bool
    message: str
    draft_id: Optional[UUID] = None
    draft: Optional[DraftDocument] = None
