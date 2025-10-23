"""
Scrape Githaf Consulting website and generate PDFs
This script will:
1. Scrape all pages from https://www.githafconsulting.com/
2. Generate PDFs from the scraped content
3. Upload to Supabase Storage
4. Create embeddings for search
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_service import process_and_store_document
from app.utils.url_scraper import scrape_url, is_valid_url
from app.utils.logger import get_logger
from typing import List, Dict

logger = get_logger(__name__)

# Pages to scrape from Githaf Consulting website
GITHAF_PAGES = [
    "https://www.githafconsulting.com/",
    "https://www.githafconsulting.com/services",
    "https://www.githafconsulting.com/about",
    "https://www.githafconsulting.com/ai-solutions",
    "https://www.githafconsulting.com/digital-transformation",
    "https://www.githafconsulting.com/software-development",
    "https://www.githafconsulting.com/contact",
]


def convert_html_to_pdf(html_content: str, title: str) -> bytes:
    """
    Convert HTML content to PDF

    Args:
        html_content: HTML content
        title: Page title

    Returns:
        bytes: PDF file content
    """
    try:
        # Try using weasyprint for HTML to PDF conversion
        from weasyprint import HTML, CSS
        from io import BytesIO

        # Add basic styling
        css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }
            h1 {
                color: #1e40af;
                border-bottom: 2px solid #1e40af;
                padding-bottom: 10px;
            }
            h2 {
                color: #3b82f6;
                margin-top: 20px;
            }
        ''')

        # Create PDF
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[css])

        logger.info(f"Generated PDF for: {title}")
        return pdf_bytes

    except ImportError:
        logger.warning("weasyprint not installed, falling back to text-only format")
        # Fallback: Just return text content as bytes
        # You can install weasyprint with: pip install weasyprint
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text(separator='\n', strip=True)
        return text_content.encode('utf-8')


async def scrape_and_create_pdf(url: str, category: str = "website") -> Dict:
    """
    Scrape URL and create PDF document

    Args:
        url: URL to scrape
        category: Document category

    Returns:
        Dict: Created document
    """
    try:
        logger.info(f"Scraping: {url}")

        # Scrape webpage (use async version)
        from app.utils.url_scraper import scrape_url_async
        scraped_data = await scrape_url_async(url)

        title = scraped_data.get("title", "Untitled Page")
        content = scraped_data.get("content", "")
        html = scraped_data.get("html", f"<html><body><h1>{title}</h1><p>{content}</p></body></html>")

        # If content is empty (JS-rendered site), create placeholder
        if not content or len(content) < 50:
            logger.warning(f"Empty or minimal content for {url}, creating placeholder")
            content = f"Page Title: {title}\n\nURL: {url}\n\nNote: This page appears to be JavaScript-rendered and content could not be extracted automatically. Please upload actual content manually or use a headless browser tool."

        # Check if we can generate PDFs
        try:
            import weasyprint
            has_weasyprint = True
        except ImportError:
            has_weasyprint = False

        # Create safe filename
        safe_title = title.replace(' ', '_').replace('/', '_').replace('\\', '_')[:50]

        # Generate PDF if weasyprint is available, otherwise save as TXT
        if has_weasyprint:
            try:
                pdf_bytes = convert_html_to_pdf(html, title)
                filename = f"{safe_title}.pdf"
            except Exception as e:
                logger.warning(f"PDF generation failed, saving as text: {e}")
                pdf_bytes = content.encode('utf-8')
                filename = f"{safe_title}.txt"
        else:
            # No weasyprint - save as text file
            logger.warning("weasyprint not installed, falling back to text-only format")
            pdf_bytes = content.encode('utf-8')
            filename = f"{safe_title}.txt"

        # Process and store document (uploads to storage + creates embeddings)
        logger.info(f"Processing document: {filename}")
        document = await process_and_store_document(
            file_content=pdf_bytes,
            filename=filename,
            source_type="scraped",
            category=category,
            source_url=url
        )

        logger.info(f"✅ Successfully created document: {document['id']}")
        logger.info(f"   - Title: {document['title']}")
        logger.info(f"   - Chunks: {document['chunk_count']}")
        logger.info(f"   - Storage: {document['storage_path']}")

        return document

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        raise


async def scrape_all_githaf_pages():
    """
    Scrape all Githaf Consulting pages and create PDFs
    """
    logger.info("=" * 80)
    logger.info("Starting Githaf Consulting Website Scraping")
    logger.info("=" * 80)

    results = {
        "success": [],
        "failed": []
    }

    for url in GITHAF_PAGES:
        try:
            logger.info(f"\n[{GITHAF_PAGES.index(url) + 1}/{len(GITHAF_PAGES)}] Processing: {url}")

            document = await scrape_and_create_pdf(url, category="githaf-website")

            results["success"].append({
                "url": url,
                "document_id": document["id"],
                "title": document["title"],
                "chunks": document["chunk_count"]
            })

            # Small delay to be respectful to the server
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
            results["failed"].append({
                "url": url,
                "error": str(e)
            })

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SCRAPING COMPLETE - SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Successfully scraped: {len(results['success'])} pages")
    logger.info(f"❌ Failed: {len(results['failed'])} pages")

    if results["success"]:
        logger.info("\nSuccessful pages:")
        for item in results["success"]:
            logger.info(f"  - {item['title']} ({item['chunks']} chunks)")

    if results["failed"]:
        logger.info("\nFailed pages:")
        for item in results["failed"]:
            logger.info(f"  - {item['url']}: {item['error']}")

    total_chunks = sum(item["chunks"] for item in results["success"])
    logger.info(f"\nTotal embeddings created: {total_chunks}")
    logger.info("=" * 80)

    return results


async def main():
    """Main entry point"""
    try:
        # Check dependencies
        try:
            import weasyprint
            logger.info("✅ weasyprint found - PDFs will be generated")
        except ImportError:
            logger.warning("⚠️  weasyprint not found - will use text format instead")
            logger.warning("   Install with: pip install weasyprint")

        # Run scraping
        results = await scrape_all_githaf_pages()

        # Exit code based on results
        if results["failed"]:
            sys.exit(1)  # Some pages failed
        else:
            sys.exit(0)  # All success

    except KeyboardInterrupt:
        logger.info("\n\nScraping interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
