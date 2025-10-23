"""
Document management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from typing import Optional, List
from pydantic import BaseModel
from app.models.document import Document, DocumentList, DocumentUpload
from app.services.document_service import (
    get_all_documents,
    process_file_upload,
    process_url,
    delete_document,
    get_document_by_id,
    get_document_full_content,
    update_document
)
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


@router.get("/", response_model=DocumentList)
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all documents in the knowledge base

    Requires authentication
    """
    try:
        documents = await get_all_documents(limit=limit, offset=offset)

        return DocumentList(
            documents=documents,
            total=len(documents)
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a document file (PDF, TXT, DOCX)

    Requires authentication
    """
    try:
        # Read file content
        file_content = await file.read()

        # Process file
        document = await process_file_upload(
            file_content=file_content,
            filename=file.filename,
            category=category
        )

        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "document": document
        }

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url")
async def add_url(
    url: str = Form(...),
    category: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a document from URL

    Requires authentication
    """
    try:
        document = await process_url(url=url, category=category)

        return {
            "success": True,
            "message": "URL content processed successfully",
            "document": document
        }

    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific document by ID

    Requires authentication
    """
    try:
        document = await get_document_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get full document content reconstructed from embedding chunks

    Requires authentication
    """
    try:
        content = await get_document_full_content(document_id)

        if content is None:
            raise HTTPException(status_code=404, detail="Document content not found")

        return {
            "success": True,
            "document_id": document_id,
            "content": content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{document_id}")
async def edit_document(
    document_id: str,
    update_request: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a document and regenerate embeddings if content changes

    Requires authentication
    """
    try:
        updated_document = await update_document(
            document_id=document_id,
            title=update_request.title,
            content=update_request.content,
            category=update_request.category
        )

        if not updated_document:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "success": True,
            "message": "Document updated successfully" + (" and embeddings regenerated" if update_request.content else ""),
            "document": updated_document
        }

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def remove_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document and its embeddings

    Requires authentication
    """
    try:
        success = await delete_document(document_id)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found or already deleted")

        return {
            "success": True,
            "message": "Document deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
