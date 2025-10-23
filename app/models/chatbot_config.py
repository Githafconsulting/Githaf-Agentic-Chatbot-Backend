"""
Chatbot Configuration Pydantic models
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class IntentPatterns(BaseModel):
    """Intent patterns configuration"""
    greeting: List[str] = Field(default_factory=list)
    farewell: List[str] = Field(default_factory=list)
    gratitude: List[str] = Field(default_factory=list)
    help: List[str] = Field(default_factory=list)
    chit_chat: List[str] = Field(default_factory=list)


class IntentEnabled(BaseModel):
    """Intent enable/disable flags"""
    greeting: bool = True
    farewell: bool = True
    gratitude: bool = True
    help: bool = True
    chit_chat: bool = True
    out_of_scope: bool = True


class TopicKeywords(BaseModel):
    """Topic keywords for trending queries"""
    services: List[str] = Field(default_factory=list)
    pricing: List[str] = Field(default_factory=list)
    contact: List[str] = Field(default_factory=list)
    hours: List[str] = Field(default_factory=list)
    process: List[str] = Field(default_factory=list)
    technology: List[str] = Field(default_factory=list)
    support: List[str] = Field(default_factory=list)
    team: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


class ChatbotConfig(BaseModel):
    """Complete chatbot configuration"""
    id: Optional[str] = None

    # Intent Configuration
    intentPatterns: Dict[str, List[str]] = Field(
        default_factory=dict,
        alias="intent_patterns",
        description="Regex patterns for each intent type"
    )
    intentEnabled: Dict[str, bool] = Field(
        default_factory=dict,
        alias="intent_enabled",
        description="Enable/disable specific intent types"
    )

    # Confidence Thresholds
    patternConfidenceThreshold: float = Field(
        default=0.7,
        alias="pattern_confidence_threshold",
        ge=0.0,
        le=1.0,
        description="Minimum confidence for pattern matching (0-1)"
    )
    llmFallbackEnabled: bool = Field(
        default=True,
        alias="llm_fallback_enabled",
        description="Use LLM for ambiguous queries"
    )
    llmConfidenceThreshold: float = Field(
        default=0.6,
        alias="llm_confidence_threshold",
        ge=0.0,
        le=1.0,
        description="Minimum confidence for LLM classification (0-1)"
    )

    # RAG Configuration
    ragTopK: int = Field(
        default=5,
        alias="rag_top_k",
        ge=1,
        le=20,
        description="Number of chunks to retrieve for RAG"
    )
    ragSimilarityThreshold: float = Field(
        default=0.5,
        alias="rag_similarity_threshold",
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for chunk retrieval (0-1)"
    )
    chunkSize: int = Field(
        default=500,
        alias="chunk_size",
        ge=100,
        le=2000,
        description="Size of text chunks for embedding"
    )
    chunkOverlap: int = Field(
        default=50,
        alias="chunk_overlap",
        ge=0,
        le=500,
        description="Overlap between consecutive chunks"
    )

    # LLM Configuration
    llmModel: str = Field(
        default="llama-3.1-8b-instant",
        alias="llm_model",
        description="LLM model name"
    )
    llmTemperature: float = Field(
        default=0.7,
        alias="llm_temperature",
        ge=0.0,
        le=2.0,
        description="LLM creativity parameter (0-1)"
    )
    llmMaxTokens: int = Field(
        default=500,
        alias="llm_max_tokens",
        ge=50,
        le=2000,
        description="Maximum tokens in LLM response"
    )

    # Topic Keywords
    topicKeywords: Dict[str, List[str]] = Field(
        default_factory=dict,
        alias="topic_keywords",
        description="Keywords for trending query categorization"
    )

    # Timestamps
    createdAt: Optional[str] = Field(None, alias="created_at")
    updatedAt: Optional[str] = Field(None, alias="updated_at")

    class Config:
        populate_by_name = True  # Accept both field name and alias when parsing
        from_attributes = True
        json_schema_extra = {
            "example": {
                "intentPatterns": {"greeting": ["^hi\\b", "^hello\\b"]},
                "intentEnabled": {"greeting": True}
            }
        }

    def model_dump(self, **kwargs):
        """Override to always use field names (camelCase) not aliases (snake_case)"""
        kwargs.setdefault('by_alias', False)  # Use field names, not aliases
        return super().model_dump(**kwargs)


class ChatbotConfigUpdate(BaseModel):
    """Chatbot configuration update (all fields optional)"""
    intentPatterns: Optional[Dict[str, List[str]]] = None
    intentEnabled: Optional[Dict[str, bool]] = None
    patternConfidenceThreshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    llmFallbackEnabled: Optional[bool] = None
    llmConfidenceThreshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    ragTopK: Optional[int] = Field(None, ge=1, le=20)
    ragSimilarityThreshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    chunkSize: Optional[int] = Field(None, ge=100, le=2000)
    chunkOverlap: Optional[int] = Field(None, ge=0, le=500)
    llmModel: Optional[str] = None
    llmTemperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llmMaxTokens: Optional[int] = Field(None, ge=50, le=2000)
    topicKeywords: Optional[Dict[str, List[str]]] = None
