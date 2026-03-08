import httpx
import trafilatura
from bs4 import BeautifulSoup
import logging
from typing import Any, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WebReaderInput(BaseModel):
    url: str = Field(description="The URL of the webpage to read")

class WebReaderTool(BaseTool):
    name: str = "web_reader"
    description: str = (
        "Extract clean text content from a URL. "
        "Optimized for news, articles, and financial reports. "
        "Uses local open-source tools (trafilatura/bs4) for extraction."
    )
    args_schema: Type[BaseModel] = WebReaderInput

    def _run(self, url: str) -> str:
        import asyncio
        return asyncio.run(self._arun(url))

    async def _arun(self, url: str) -> str:
        """Fetch and extract webpage content."""
        if not url.startswith("http"):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html = response.text

            # 1. Try Trafilatura for clean Markdown extraction
            content = trafilatura.extract(html, include_links=True, include_comments=False)
            
            if not content:
                # 2. Fallback to BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                # Remove noise
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                content = soup.get_text(separator="\n", strip=True)

            if not content:
                return "Error: Could not extract meaningful content from the page."

            # Truncate for token safety (8000 chars should be enough for most articles)
            if len(content) > 8000:
                content = content[:8000] + "\n... (content truncated)"

            return content
        except Exception as e:
            logger.error(f"WebReaderTool error for {url}: {e}")
            return f"Error reading URL: {str(e)}"
