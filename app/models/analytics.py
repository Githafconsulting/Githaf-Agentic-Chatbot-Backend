"""
Analytics and metrics Pydantic models
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationMetrics(BaseModel):
    """Conversation-related metrics"""
    total_conversations: int
    avg_messages_per_conversation: float
    total_messages: int
    conversations_today: int
    avg_conversation_duration_seconds: float = Field(..., description="Average conversation duration in seconds (lifespan)")
    avg_active_chat_time_seconds: float = Field(..., description="Average active chat time in seconds (engagement time)")


class SatisfactionMetrics(BaseModel):
    """User satisfaction metrics"""
    avg_satisfaction: float = Field(..., description="Average satisfaction score (0-1)")
    feedback_rate: float = Field(..., description="Percentage of messages with feedback")
    total_feedback: int
    positive_feedback: int = Field(..., description="Thumbs up count")
    negative_feedback: int = Field(..., description="Thumbs down count")


class TrendingQuery(BaseModel):
    """Trending query information (intent-based)"""
    intent: str = Field(..., description="Intent or topic name")
    query: str = Field(..., description="Display name for the intent/topic")
    count: int = Field(..., description="Number of queries with this intent")
    sample_queries: List[str] = Field(default_factory=list, description="Sample queries showing different phrasings")
    avg_rating: Optional[float] = None


class KnowledgeBaseMetrics(BaseModel):
    """Knowledge base metrics"""
    total_documents: int
    total_chunks: int
    documents_added_this_month: int


class AnalyticsOverview(BaseModel):
    """Complete analytics overview"""
    conversation_metrics: ConversationMetrics
    satisfaction_metrics: SatisfactionMetrics
    trending_queries: List[TrendingQuery]
    knowledge_base_metrics: KnowledgeBaseMetrics
    last_updated: datetime


class FlaggedQuery(BaseModel):
    """Flagged query needing review"""
    feedback_id: str = Field(..., description="Actual feedback ID for soft-delete operations")
    message_id: str
    conversation_id: Optional[str] = None
    query: str
    response: str
    rating: Optional[int]
    comment: Optional[str] = None
    created_at: datetime
    reason: str = Field(..., description="Why it was flagged")
