"""
Supabase Storage service for file management
"""
from typing import Optional, Dict, Any, BinaryIO
import mimetypes
import os
from datetime import datetime
from app.core.database import get_supabase_client
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

STORAGE_BUCKET = "documents"


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename

    Args:
        filename: File name

    Returns:
        str: MIME type
    """
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        return mime_type

    # Fallback based on extension
    ext = filename.lower().split('.')[-1]
    mime_types = {
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword'
    }

    return mime_types.get(ext, 'application/octet-stream')


def generate_storage_path(filename: str, category: Optional[str] = None) -> str:
    """
    Generate unique storage path for file

    Args:
        filename: Original filename
        category: Optional category folder

    Returns:
        str: Storage path (e.g., "general/2025/10/uuid_filename.pdf")
    """
    from uuid import uuid4

    # Get file extension
    ext = filename.split('.')[-1] if '.' in filename else 'bin'

    # Generate timestamp-based folder structure
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')

    # Generate unique filename
    unique_id = str(uuid4())[:8]
    safe_filename = filename.replace(' ', '_').replace('..', '_')
    unique_filename = f"{unique_id}_{safe_filename}"

    # Build path
    if category:
        path = f"{category}/{year}/{month}/{unique_filename}"
    else:
        path = f"general/{year}/{month}/{unique_filename}"

    return path


async def upload_file_to_storage(
    file_content: bytes,
    filename: str,
    category: Optional[str] = None,
    bucket: str = STORAGE_BUCKET
) -> Dict[str, Any]:
    """
    Upload file to Supabase Storage

    Args:
        file_content: File bytes
        filename: Original filename
        category: Optional category for organization
        bucket: Storage bucket name

    Returns:
        Dict with storage_path, public_url, file_size

    Raises:
        Exception: If upload fails
    """
    try:
        client = get_supabase_client()

        # Generate unique storage path
        storage_path = generate_storage_path(filename, category)

        # Get MIME type
        content_type = get_mime_type(filename)

        # Get file size
        file_size = len(file_content)

        logger.info(f"Uploading file: {filename} ({file_size} bytes) to {storage_path}")

        # Upload to storage
        response = client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_content,
            file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false"  # Don't overwrite if exists
            }
        )

        # Generate public URL (requires auth to access since bucket is private)
        public_url = client.storage.from_(bucket).get_public_url(storage_path)

        # For private buckets, create signed URL (valid for 1 hour)
        signed_url = client.storage.from_(bucket).create_signed_url(
            storage_path,
            expires_in=3600  # 1 hour
        )

        download_url = signed_url.get('signedURL') if signed_url else public_url

        logger.info(f"File uploaded successfully: {storage_path}")

        return {
            "storage_path": storage_path,
            "public_url": public_url,
            "download_url": download_url,
            "file_size": file_size,
            "content_type": content_type
        }

    except Exception as e:
        logger.error(f"Error uploading file to storage: {e}")
        raise Exception(f"Failed to upload file: {str(e)}")


async def get_file_from_storage(
    storage_path: str,
    bucket: str = STORAGE_BUCKET
) -> bytes:
    """
    Download file from Supabase Storage

    Args:
        storage_path: Path to file in storage
        bucket: Storage bucket name

    Returns:
        bytes: File content

    Raises:
        Exception: If download fails
    """
    try:
        client = get_supabase_client()

        logger.info(f"Downloading file from storage: {storage_path}")

        # Download file
        response = client.storage.from_(bucket).download(storage_path)

        logger.info(f"File downloaded successfully: {storage_path}")

        return response

    except Exception as e:
        logger.error(f"Error downloading file from storage: {e}")
        raise Exception(f"Failed to download file: {str(e)}")


async def delete_file_from_storage(
    storage_path: str,
    bucket: str = STORAGE_BUCKET
) -> bool:
    """
    Delete file from Supabase Storage

    Args:
        storage_path: Path to file in storage
        bucket: Storage bucket name

    Returns:
        bool: True if successful

    Raises:
        Exception: If deletion fails
    """
    try:
        client = get_supabase_client()

        logger.info(f"Deleting file from storage: {storage_path}")

        # Delete file
        response = client.storage.from_(bucket).remove([storage_path])

        logger.info(f"File deleted successfully: {storage_path}")

        return True

    except Exception as e:
        logger.error(f"Error deleting file from storage: {e}")
        return False


async def get_signed_download_url(
    storage_path: str,
    expires_in: int = 3600,
    bucket: str = STORAGE_BUCKET
) -> str:
    """
    Generate signed URL for file download (for private buckets)

    Args:
        storage_path: Path to file in storage
        expires_in: URL expiration time in seconds (default 1 hour)
        bucket: Storage bucket name

    Returns:
        str: Signed download URL

    Raises:
        Exception: If URL generation fails
    """
    try:
        client = get_supabase_client()

        # logger.debug(f"Generating signed URL for: {storage_path}")

        # Create signed URL
        response = client.storage.from_(bucket).create_signed_url(
            storage_path,
            expires_in=expires_in
        )

        signed_url = response.get('signedURL')

        if not signed_url:
            raise Exception("Failed to generate signed URL")

        # logger.debug(f"Signed URL generated successfully")

        return signed_url

    except Exception as e:
        logger.error(f"Error generating signed URL: {e}")
        raise Exception(f"Failed to generate download URL: {str(e)}")


async def list_files_in_storage(
    folder_path: Optional[str] = None,
    bucket: str = STORAGE_BUCKET
) -> list:
    """
    List files in storage bucket or folder

    Args:
        folder_path: Optional folder path to list
        bucket: Storage bucket name

    Returns:
        list: List of file objects
    """
    try:
        client = get_supabase_client()

        logger.info(f"Listing files in storage: {folder_path or 'root'}")

        # List files
        if folder_path:
            response = client.storage.from_(bucket).list(folder_path)
        else:
            response = client.storage.from_(bucket).list()

        logger.info(f"Found {len(response)} files/folders")

        return response

    except Exception as e:
        logger.error(f"Error listing files in storage: {e}")
        return []


async def get_storage_stats(bucket: str = STORAGE_BUCKET) -> Dict[str, Any]:
    """
    Get storage usage statistics

    Args:
        bucket: Storage bucket name

    Returns:
        Dict with total_files, total_size, etc.
    """
    try:
        files = await list_files_in_storage(bucket=bucket)

        total_files = len(files)
        total_size = sum(f.get('metadata', {}).get('size', 0) for f in files)

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "bucket": bucket
        }

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "bucket": bucket,
            "error": str(e)
        }
