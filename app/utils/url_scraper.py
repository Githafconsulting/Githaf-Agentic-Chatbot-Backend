"""
URL scraping utility for extracting web content using Playwright
"""
from typing import Optional, Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def scrape_url_async(url: str, timeout: int = 30000) -> Dict[str, str]:
    """
    Async version: Scrape text content from a URL using Playwright (handles JavaScript-rendered sites)

    Args:
        url: URL to scrape
        timeout: Request timeout in milliseconds (default: 30000ms = 30s)

    Returns:
        Dict containing title, content, html, and url

    Raises:
        ValueError: If scraping fails
    """
    try:
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)

            # Create new page
            page = await browser.new_page()

            # Set longer timeout for slow websites
            page.set_default_timeout(timeout)

            # Navigate to URL
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until='networkidle')

            # Wait a bit for any dynamic content to load
            await page.wait_for_timeout(2000)

            # Get page title
            title = await page.title() or "No title"

            # Get full HTML content (after JavaScript execution)
            html_content = await page.content()

            # Close browser
            await browser.close()

            # Parse with BeautifulSoup for text extraction (sync operation)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script, style, nav, footer, header elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')

            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)

            # Clean up text (remove excessive newlines)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n\n'.join(lines)

            logger.info(f"Successfully scraped {url}, extracted {len(content)} characters")

            return {
                "title": title,
                "content": content,
                "html": html_content,  # Full rendered HTML
                "url": url
            }

    except PlaywrightTimeout as e:
        logger.error(f"Timeout scraping URL {url}: {e}")
        raise ValueError(f"Timeout fetching URL (took longer than {timeout/1000}s)")
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {e}")
        raise ValueError(f"Failed to scrape URL: {str(e)}")


def scrape_url(url: str, timeout: int = 30000) -> Dict[str, str]:
    """
    Sync wrapper for async scrape function (for backwards compatibility)

    Args:
        url: URL to scrape
        timeout: Request timeout in milliseconds

    Returns:
        Dict containing title, content, html, and url
    """
    import asyncio
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, raise error
            raise RuntimeError("scrape_url (sync) cannot be called from async context. Use scrape_url_async instead.")
        else:
            return loop.run_until_complete(scrape_url_async(url, timeout))
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(scrape_url_async(url, timeout))


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL

    Args:
        url: URL string to validate

    Returns:
        bool: True if valid
    """
    try:
        result = requests.utils.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
