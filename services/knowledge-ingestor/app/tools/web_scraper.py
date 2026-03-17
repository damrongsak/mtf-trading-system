import httpx
from typing import Optional
from bs4 import BeautifulSoup
from app.core.logger import get_logger

logger = get_logger("WebScraper")

class WebScraperTool:
    """
    Simple tool to scrape text from a URL.
    """

    @staticmethod
    async def scrape_url(url: str) -> Optional[str]:
        """Fetch content from URL and extract text."""
        logger.info(f"🌐 Scraping URL: {url}")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text
                text = soup.get_text()
                
                # Break into lines and remove leading and trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # Drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                return text
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}", extra={"url": url, "error": str(e)})
            return None

if __name__ == "__main__":
    import asyncio
    async def test():
        text = await WebScraperTool.scrape_url("https://www.google.com")
        print(text[:500])
    asyncio.run(test())
