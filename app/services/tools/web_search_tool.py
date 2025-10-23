"""
Web Search Tool (Phase 5: Tool Ecosystem)
Search the web for up-to-date information
"""
from typing import Dict, Any, List, Optional
from app.services.tools.tools_registry import Tool, ToolCategory
from app.utils.logger import get_logger
import httpx
import os
from bs4 import BeautifulSoup

logger = get_logger(__name__)


class WebSearchTool(Tool):
    """Tool for web searching"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for current information",
            category=ToolCategory.SEARCH,
            enabled=True,
            requires_auth=False
        )

        # API configuration (supports DuckDuckGo, SerpAPI, or custom)
        self.search_provider = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # duckduckgo, serpapi
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate search parameters"""
        if "query" not in params:
            logger.error("Missing required field: query")
            return False

        if not params["query"].strip():
            logger.error("Query cannot be empty")
            return False

        return True

    def get_schema(self) -> Dict[str, Any]:
        """Get parameter schema"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "minimum": 1,
                    "maximum": 10
                },
                "safe_search": {
                    "type": "boolean",
                    "description": "Enable safe search (default: true)"
                }
            },
            "required": ["query"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform web search

        Args:
            params: Search parameters (query, num_results, safe_search)

        Returns:
            Search results
        """
        query = params["query"]
        num_results = params.get("num_results", 5)

        logger.info(f"Searching web for: {query}")

        if self.search_provider == "serpapi" and self.serpapi_key:
            return await self._search_serpapi(query, num_results)
        else:
            # Fallback to DuckDuckGo HTML scraping
            return await self._search_duckduckgo(query, num_results)

    async def _search_serpapi(self, query: str, num_results: int) -> Dict[str, Any]:
        """
        Search using SerpAPI (Google Search API)

        Args:
            query: Search query
            num_results: Number of results

        Returns:
            Search results
        """
        logger.info(f"Searching via SerpAPI: {query}")

        try:
            async with httpx.AsyncClient() as client:
                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": self.serpapi_key,
                    "num": num_results,
                    "engine": "google"
                }

                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                # Extract organic results
                organic_results = data.get("organic_results", [])

                results = []
                for item in organic_results[:num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("displayed_link", "")
                    })

                logger.info(f"Found {len(results)} results via SerpAPI")

                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "provider": "serpapi"
                }

        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "serpapi"
            }

    async def _search_duckduckgo(self, query: str, num_results: int) -> Dict[str, Any]:
        """
        Search using DuckDuckGo HTML scraping (fallback, no API key needed)

        Args:
            query: Search query
            num_results: Number of results

        Returns:
            Search results
        """
        logger.info(f"Searching via DuckDuckGo: {query}")

        try:
            async with httpx.AsyncClient() as client:
                url = "https://html.duckduckgo.com/html/"
                params = {"q": query}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                response = await client.post(url, data=params, headers=headers, timeout=10.0)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")

                results = []
                result_divs = soup.find_all("div", class_="result", limit=num_results)

                for div in result_divs:
                    # Extract title and link
                    title_tag = div.find("a", class_="result__a")
                    snippet_tag = div.find("a", class_="result__snippet")

                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        link = title_tag.get("href", "")
                        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "DuckDuckGo"
                        })

                logger.info(f"Found {len(results)} results via DuckDuckGo")

                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "provider": "duckduckgo"
                }

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "duckduckgo"
            }


async def quick_search(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
    """
    Quick web search helper function

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        List of search results
    """
    tool = WebSearchTool()

    result = await tool.execute({
        "query": query,
        "num_results": num_results
    })

    if result.get("success"):
        return result.get("results", [])
    else:
        logger.warning(f"Search failed: {result.get('error')}")
        return []
