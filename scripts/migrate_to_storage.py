"""
Data Migration Script: Migrate existing documents to new 3-layer architecture

This script will:
1. Read all documents from documents_backup table (old schema with full text)
2. Generate PDFs from the text content
3. Upload PDFs to Supabase Storage
4. Create metadata records in new documents table
5. Keep existing embeddings (they reference document_id, so they'll still work)
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_supabase_client
from app.services.storage_service import upload_file_to_storage
from app.utils.logger import get_logger

logger = get_logger(__name__)


def text_to_pdf(text_content: str, title: str) -> bytes:
    """
    Convert text content to PDF

    Args:
        text_content: Text content
        title: Document title

    Returns:
        bytes: PDF file content
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO

        buffer = BytesIO()

        # Create PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        # Container for 'Flowable' objects
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#1e40af',
            spaceAfter=30,
        )
        body_style = styles['BodyText']

        # Add title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.2*inch))

        # Add content
        # Split text into paragraphs
        paragraphs = text_content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para.replace('\n', '<br/>'), body_style))
                elements.append(Spacer(1, 0.1*inch))

        # Build PDF
        doc.build(elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"Generated PDF ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except ImportError:
        logger.warning("reportlab not installed, using plain text format")
        # Fallback to text file
        return text_content.encode('utf-8')


async def migrate_document(old_doc: dict) -> dict:
    """
    Migrate a single document from old schema to new schema

    Args:
        old_doc: Old document record with 'content' field

    Returns:
        dict: New document record
    """
    try:
        client = get_supabase_client()

        doc_id = old_doc["id"]
        content = old_doc.get("content", "")
        metadata = old_doc.get("metadata", {})

        # Extract info from metadata
        title = metadata.get("filename") or metadata.get("title") or f"Document_{doc_id[:8]}"
        source_type = metadata.get("source", "upload")
        source_url = metadata.get("url")
        category = metadata.get("category")

        logger.info(f"Migrating document: {title}")

        # Determine file type from metadata or default to txt
        file_type = "txt"
        if "filename" in metadata:
            ext = metadata["filename"].split('.')[-1].lower()
            if ext in ['pdf', 'docx', 'txt']:
                file_type = ext

        # Generate PDF or text file from content
        if file_type == 'pdf' or len(content) > 1000:
            # Large content - create PDF
            file_content = text_to_pdf(content, title)
            filename = f"{title}.pdf"
        else:
            # Small content - keep as text
            file_content = content.encode('utf-8')
            filename = f"{title}.txt"

        # Upload to Storage
        logger.info(f"Uploading to storage: {filename}")
        storage_result = await upload_file_to_storage(
            file_content=file_content,
            filename=filename,
            category=category or "migrated"
        )

        # Create new document record
        new_doc_data = {
            "id": doc_id,  # Keep same ID so embeddings still work
            "title": title,
            "file_type": file_type,
            "file_size": storage_result["file_size"],
            "storage_path": storage_result["storage_path"],
            "download_url": storage_result["download_url"],
            "source_type": source_type,
            "source_url": source_url,
            "category": category,
            "summary": content[:500] if content else None,
            "chunk_count": 0,  # Will be counted from embeddings
            "metadata": metadata,
            "created_at": old_doc.get("created_at")
        }

        # Insert into new documents table
        response = client.table("documents").insert(new_doc_data).execute()

        if not response.data:
            raise Exception("Failed to insert document")

        new_doc = response.data[0]

        # Count existing embeddings for this document
        embeddings_count = client.table("embeddings").select("id", count="exact").eq("document_id", doc_id).execute()
        chunk_count = embeddings_count.count if embeddings_count else 0

        # Update chunk count
        client.table("documents").update({"chunk_count": chunk_count}).eq("id", doc_id).execute()

        logger.info(f"✅ Migrated: {title} ({chunk_count} chunks)")

        return new_doc

    except Exception as e:
        logger.error(f"Error migrating document {old_doc.get('id')}: {e}")
        raise


async def migrate_all_documents():
    """
    Migrate all documents from old schema to new schema
    """
    try:
        client = get_supabase_client()

        logger.info("=" * 80)
        logger.info("STARTING DOCUMENT MIGRATION")
        logger.info("=" * 80)

        # Check if backup table exists
        try:
            backup_docs_response = client.table("documents_backup").select("*").execute()
            old_documents = backup_docs_response.data if backup_docs_response.data else []
        except Exception as e:
            logger.error("documents_backup table not found. Run SQL migration first!")
            logger.error("Execute: migrate_documents_schema.sql")
            return {"success": [], "failed": []}

        logger.info(f"Found {len(old_documents)} documents to migrate")

        results = {
            "success": [],
            "failed": []
        }

        for idx, old_doc in enumerate(old_documents):
            try:
                logger.info(f"\n[{idx + 1}/{len(old_documents)}] Migrating document...")

                new_doc = await migrate_document(old_doc)

                results["success"].append({
                    "id": new_doc["id"],
                    "title": new_doc["title"],
                    "chunks": new_doc.get("chunk_count", 0)
                })

            except Exception as e:
                logger.error(f"Failed to migrate document: {e}")
                results["failed"].append({
                    "id": old_doc.get("id", "unknown"),
                    "error": str(e)
                })

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION COMPLETE - SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Successfully migrated: {len(results['success'])} documents")
        logger.info(f"❌ Failed: {len(results['failed'])} documents")

        if results["success"]:
            logger.info("\nMigrated documents:")
            for item in results["success"]:
                logger.info(f"  - {item['title']} ({item['chunks']} chunks)")

        if results["failed"]:
            logger.info("\nFailed documents:")
            for item in results["failed"]:
                logger.info(f"  - {item['id']}: {item['error']}")

        logger.info("=" * 80)

        return results

    except Exception as e:
        logger.error(f"Fatal error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise


async def main():
    """Main entry point"""
    try:
        # Check dependencies
        try:
            import reportlab
            logger.info("✅ reportlab found - PDFs will be generated")
        except ImportError:
            logger.warning("⚠️  reportlab not found - will use text format")
            logger.warning("   Install with: pip install reportlab")

        # Run migration
        results = await migrate_all_documents()

        # Exit code
        if results["failed"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
