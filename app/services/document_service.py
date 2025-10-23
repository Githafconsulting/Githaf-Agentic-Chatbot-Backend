"""
Document processing service - Refactored for 3-layer architecture
Layer 1: Supabase Storage (original files)
Layer 2: Documents table (metadata only)
Layer 3: Embeddings table (searchable chunks)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from app.core.database import get_supabase_client
from app.utils.file_parser import parse_file
from app.utils.url_scraper import scrape_url, is_valid_url
from app.utils.text_processor import chunk_text
from app.services.embedding_service import get_embeddings_batch
from app.services.vectorstore_service import store_embeddings_batch, delete_embeddings_by_document
from app.services.storage_service import (
    upload_file_to_storage,
    delete_file_from_storage,
    get_signed_download_url
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_document_metadata(
    title: str,
    file_type: str,
    storage_path: str,
    download_url: str,
    source_type: str,
    file_size: Optional[int] = None,
    source_url: Optional[str] = None,
    category: Optional[str] = None,
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create document metadata record (Layer 2)

    Args:
        title: Document title
        file_type: File type (pdf, txt, docx, etc.)
        storage_path: Path in Supabase Storage
        download_url: Signed download URL
        source_type: upload, url, or scraped
        file_size: File size in bytes
        source_url: Original URL if from web
        category: Document category
        summary: Optional summary
        metadata: Additional metadata

    Returns:
        Dict: Created document record
    """
    try:
        client = get_supabase_client()

        data = {
            "title": title,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "download_url": download_url,
            "source_type": source_type,
            "source_url": source_url,
            "category": category,
            "summary": summary[:500] if summary else None,  # Limit summary to 500 chars
            "chunk_count": 0,  # Will be updated after embeddings created
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }

        response = client.table("documents").insert(data).execute()

        document = response.data[0] if response.data else None

        logger.info(f"Created document metadata: {document.get('id')}")

        return document

    except Exception as e:
        logger.error(f"Error creating document metadata: {e}")
        raise


async def update_document_chunk_count(document_id: str, chunk_count: int) -> bool:
    """
    Update document's chunk count

    Args:
        document_id: Document ID
        chunk_count: Number of chunks/embeddings

    Returns:
        bool: True if successful
    """
    try:
        client = get_supabase_client()

        response = client.table("documents").update({
            "chunk_count": chunk_count
        }).eq("id", document_id).execute()

        logger.info(f"Updated chunk count for document {document_id}: {chunk_count}")

        return True

    except Exception as e:
        logger.error(f"Error updating chunk count: {e}")
        return False


async def process_and_store_document(
    file_content: bytes,
    filename: str,
    source_type: str,
    category: Optional[str] = None,
    source_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete document processing pipeline:
    1. Upload file to Storage (Layer 1)
    2. Create metadata record (Layer 2)
    3. Extract text, chunk, and create embeddings (Layer 3)

    Args:
        file_content: File bytes
        filename: Original filename
        source_type: upload, url, or scraped
        category: Optional category
        source_url: Original URL if from web

    Returns:
        Dict: Created document with all metadata
    """
    try:
        # Step 1: Upload file to Supabase Storage (Layer 1)
        logger.info(f"Uploading file to storage: {filename}")
        storage_result = await upload_file_to_storage(
            file_content=file_content,
            filename=filename,
            category=category
        )

        storage_path = storage_result["storage_path"]
        download_url = storage_result["download_url"]
        file_size = storage_result["file_size"]

        # Determine file type
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'

        # Step 2: Extract text content (temporarily, in memory only)
        logger.info(f"Extracting text from file: {filename}")
        text_content = parse_file(file_content, filename)

        # Generate summary (first 500 chars of content)
        summary = text_content[:500] if text_content else None

        # Step 3: Create metadata record (Layer 2 - NO full text stored)
        logger.info(f"Creating document metadata")
        document = await create_document_metadata(
            title=filename,
            file_type=file_type,
            storage_path=storage_path,
            download_url=download_url,
            source_type=source_type,
            file_size=file_size,
            source_url=source_url,
            category=category,
            summary=summary
        )

        document_id = document["id"]

        # Step 4: Chunk text (Layer 3 preparation)
        logger.info(f"Chunking text content")
        chunks = chunk_text(text_content)
        logger.info(f"Document chunked into {len(chunks)} pieces")

        # Step 5: Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = await get_embeddings_batch(chunks)

        # Step 6: Prepare embedding records (Layer 3)
        embedding_records = []
        for chunk, embedding in zip(chunks, embeddings):
            embedding_records.append({
                "document_id": document_id,
                "chunk_text": chunk,
                "embedding": embedding  # Stored as list, Supabase converts to vector
            })

        # Step 7: Store embeddings in batch
        logger.info(f"Storing {len(embedding_records)} embeddings")
        stored_embeddings = await store_embeddings_batch(embedding_records)

        # Step 8: Update chunk count in metadata
        await update_document_chunk_count(document_id, len(stored_embeddings))

        # Step 9: Discard extracted text (it's now in chunks, no longer needed)
        # Python garbage collection will handle this automatically
        text_content = None

        logger.info(f"Document processing complete: {document_id}")

        # Return enriched document info
        document["chunk_count"] = len(stored_embeddings)
        document["storage_url"] = storage_result["public_url"]

        return document

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise


async def process_file_upload(
    file_content: bytes,
    filename: str,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process uploaded file

    Args:
        file_content: File bytes
        filename: Original filename
        category: Optional category

    Returns:
        Dict: Created document
    """
    try:
        logger.info(f"Processing file upload: {filename}")

        document = await process_and_store_document(
            file_content=file_content,
            filename=filename,
            source_type="upload",
            category=category
        )

        return document

    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        raise


async def process_url(url: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Process URL by scraping content and creating PDF

    Args:
        url: URL to scrape
        category: Optional category

    Returns:
        Dict: Created document
    """
    try:
        # Validate URL
        if not is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        logger.info(f"Processing URL: {url}")

        # Scrape content
        scraped_data = scrape_url(url)

        content = scraped_data["content"]
        title = scraped_data.get("title", "Untitled")

        # Generate PDF from scraped content
        # For now, we'll store as TXT - PDF generation can be added later
        filename = f"{title.replace(' ', '_')[:50]}.txt"
        file_content = content.encode('utf-8')

        document = await process_and_store_document(
            file_content=file_content,
            filename=filename,
            source_type="url",
            category=category,
            source_url=url
        )

        return document

    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        raise


async def get_all_documents(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get all documents from knowledge base (metadata only)

    Args:
        limit: Maximum number of documents
        offset: Offset for pagination

    Returns:
        List[Dict]: List of documents
    """
    try:
        client = get_supabase_client()

        response = client.table("documents").select(
            "*"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        documents = response.data if response.data else []

        # Generate fresh signed URLs for downloads
        for doc in documents:
            if doc.get("storage_path"):
                try:
                    signed_url = await get_signed_download_url(doc["storage_path"])
                    doc["download_url"] = signed_url
                except Exception as e:
                    logger.warning(f"Could not generate signed URL for {doc['id']}: {e}")

        # logger.debug(f"Retrieved {len(documents)} documents")

        return documents

    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return []


async def delete_document(document_id: str) -> bool:
    """
    Delete a document and its embeddings (all 3 layers)

    If document was auto-published from a draft, clears the draft's published_document_id
    to make the feedback available for reuse.

    Args:
        document_id: Document ID

    Returns:
        bool: True if successful
    """
    try:
        client = get_supabase_client()

        # Step 1: Get document to find storage_path and check if from draft
        doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()

        if not doc_response.data:
            logger.warning(f"Document not found: {document_id}")
            return False

        document = doc_response.data
        storage_path = document.get("storage_path")
        source_type = document.get("source_type")
        metadata = document.get("metadata", {})
        draft_id = metadata.get("draft_id")

        # Step 2: If document was auto-published from a draft, clear the reference FIRST
        # (Foreign key constraint requires this before document deletion)
        if source_type == "draft_published" and draft_id:
            logger.info(f"Document was auto-published from draft {draft_id}, clearing reference first")

            # Clear the published_document_id to make feedback available again
            client.table("draft_documents").update({
                "published_document_id": None,
                "published_at": None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", draft_id).execute()

            logger.info(f"Feedback recycled: draft {draft_id} can now be republished or feedback reused")

        # Step 3: Delete embeddings (Layer 3)
        logger.info(f"Deleting embeddings for document: {document_id}")
        await delete_embeddings_by_document(document_id)

        # Step 4: Delete file from storage (Layer 1) - only for uploaded/scraped files
        if storage_path:
            logger.info(f"Deleting file from storage: {storage_path}")
            await delete_file_from_storage(storage_path)

        # Step 5: Delete metadata record (Layer 2)
        logger.info(f"Deleting document metadata: {document_id}")
        client.table("documents").delete().eq("id", document_id).execute()

        logger.info(f"Document deleted successfully: {document_id}")

        return True

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return False


async def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific document by ID (with fresh download URL)

    Args:
        document_id: Document ID

    Returns:
        Dict: Document record or None
    """
    try:
        client = get_supabase_client()

        response = client.table("documents").select("*").eq("id", document_id).single().execute()

        if not response.data:
            return None

        document = response.data

        # Generate fresh signed download URL
        if document.get("storage_path"):
            try:
                signed_url = await get_signed_download_url(document["storage_path"])
                document["download_url"] = signed_url
            except Exception as e:
                logger.warning(f"Could not generate signed URL: {e}")

        return document

    except Exception as e:
        logger.error(f"Error getting document: {e}")
        return None


async def get_document_full_content(document_id: str) -> Optional[str]:
    """
    Reconstruct full document content from embedding chunks

    Args:
        document_id: Document ID

    Returns:
        str: Full document content or None
    """
    try:
        client = get_supabase_client()

        # Get all embedding chunks for this document
        chunks_response = client.table("embeddings").select(
            "chunk_text"
        ).eq("document_id", document_id).order("created_at", desc=False).execute()

        if not chunks_response.data:
            logger.warning(f"No chunks found for document: {document_id}")
            return None

        chunks = chunks_response.data

        # Reconstruct full text from chunks
        # Note: Chunks may have overlap, so we need to be smart about reassembly
        full_content = ""

        for i, chunk_data in enumerate(chunks):
            content = chunk_data.get("chunk_text", "")

            if i == 0:
                # First chunk - add in full
                full_content = content
            else:
                # Subsequent chunks - try to remove overlap
                # Look for overlap with end of existing content
                overlap_found = False
                for overlap_size in range(min(100, len(content)), 0, -1):
                    chunk_start = content[:overlap_size]
                    if full_content.endswith(chunk_start):
                        # Found overlap, add only the non-overlapping part
                        full_content += content[overlap_size:]
                        overlap_found = True
                        break

                if not overlap_found:
                    # No overlap found, add with separator
                    full_content += "\n\n" + content

        logger.info(f"Reconstructed content for document {document_id}: {len(full_content)} characters from {len(chunks)} chunks")

        return full_content

    except Exception as e:
        logger.error(f"Error getting document full content: {e}")
        return None


async def update_document(
    document_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update a document and regenerate embeddings if content changes

    Args:
        document_id: Document ID
        title: New title (optional)
        content: New content (optional, triggers embedding regeneration)
        category: New category (optional)

    Returns:
        Dict: Updated document
    """
    try:
        client = get_supabase_client()

        # Get existing document
        doc_response = client.table("documents").select("*").eq("id", document_id).single().execute()

        if not doc_response.data:
            raise ValueError(f"Document not found: {document_id}")

        document = doc_response.data

        # Prepare update data
        update_data = {}

        if title:
            update_data["title"] = title

        if category is not None:
            update_data["category"] = category

        if content:
            # Generate new summary from content
            update_data["summary"] = content[:500] if content else None

        # Update metadata if there are changes
        if update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
            client.table("documents").update(update_data).eq("id", document_id).execute()
            logger.info(f"Updated document metadata: {document_id}")

        # If content changed, regenerate embeddings
        if content:
            logger.info(f"Content updated, regenerating embeddings for document: {document_id}")

            # Step 1: Delete old embeddings
            logger.info(f"Deleting old embeddings")
            await delete_embeddings_by_document(document_id)

            # Step 2: Chunk new content
            logger.info(f"Chunking new content")
            chunks = chunk_text(content)
            logger.info(f"Document chunked into {len(chunks)} pieces")

            # Step 3: Generate embeddings for new chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = await get_embeddings_batch(chunks)

            # Step 4: Prepare embedding records
            embedding_records = []
            for chunk, embedding in zip(chunks, embeddings):
                embedding_records.append({
                    "document_id": document_id,
                    "chunk_text": chunk,
                    "embedding": embedding
                })

            # Step 5: Store new embeddings
            logger.info(f"Storing {len(embedding_records)} new embeddings")
            stored_embeddings = await store_embeddings_batch(embedding_records)

            # Step 6: Update chunk count
            await update_document_chunk_count(document_id, len(stored_embeddings))

            logger.info(f"Embeddings regenerated successfully: {document_id}")

        # Return updated document
        updated_doc = await get_document_by_id(document_id)
        return updated_doc

    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise
