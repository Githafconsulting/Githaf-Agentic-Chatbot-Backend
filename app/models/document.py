"""
Document and knowledge base Pydantic models
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID


class Document(BaseModel):
    """Document database model - 3-layer architecture (metadata only)"""
    id: UUID
    title: str
    file_type: str  # pdf, txt, docx, html, webpage
    file_size: Optional[int] = None  # Size in bytes
    storage_path: Optional[str] = None  # Path in Supabase Storage
    download_url: Optional[str] = None  # Signed download URL
    source_type: str  # upload, url, scraped
    source_url: Optional[str] = None  # Original URL if from web
    category: Optional[str] = None
    summary: Optional[str] = None  # 200-500 char summary (NOT full content)
    chunk_count: int = 0  # Number of embeddings
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata as JSON
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentCreate(BaseModel):
    """Model for creating a new document"""
    title: str
    file_type: str
    file_size: Optional[int] = None
    storage_path: str
    download_url: str
    source_type: str
    source_url: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentUpload(BaseModel):
    """Model for document upload"""
    source: str = Field(..., description="Source type")
    category: Optional[str] = None
    url: Optional[str] = None


class DocumentList(BaseModel):
    """List of documents"""
    documents: List[Document]
    total: int


class Embedding(BaseModel):
    """Embedding database model"""
    id: UUID
    document_id: UUID
    chunk_text: str
    embedding: List[float]
    created_at: datetime


class EmbeddingCreate(BaseModel):
    """Model for creating a new embedding"""
    document_id: UUID
    chunk_text: str
    embedding: List[float]
