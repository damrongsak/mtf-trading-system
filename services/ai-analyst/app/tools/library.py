from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.services.rag import RAGService
import logging

logger = logging.getLogger(__name__)

class LibrarySearchInput(BaseModel):
    query: str = Field(description="The semantic search query to find relevant information in the quantitative trading library.")
    limit: int = Field(default=5, description="Number of relevant chunks to retrieve.")
    collection: Optional[str] = Field(default=None, description="The specific Qdrant collection to search (e.g., 'trading_psychology'). If omitted, searches 'quant_library'.")

class SearchQuantLibraryTool(BaseTool):
    name: str = "search_quant_library"
    description: str = (
        "Searches institutional-grade quantitative trading books, research, and technical guides. "
        "Use this for understanding Smart Money Concepts (SMC), risk management theories (Kelly, etc.), "
        "and advanced market mechanics to build or refine strategies. "
        "Can search specific collections like 'trading_psychology' if provided."
    )
    args_schema: Any = LibrarySearchInput
    rag_service: Any = Field(exclude=True) # Runtime dependency

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        query = ""
        limit = 5
        collection = None
        
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
            limit = input_data.get("limit", 5)
            collection = input_data.get("collection")
        elif isinstance(input_data, str):
            query = input_data
            
        if not query:
            return "No search query provided."

        try:
            # search_library returns list[dict] with 'content', 'score', 'filename'
            results = await self.rag_service.search_library(
                query=query,
                limit=limit,
                expand_context=True,
                collection=collection
            )
            
            if not results:
                target = f"collection '{collection}'" if collection else "the quant library"
                return f"No relevant information found in {target} for: '{query}'"
            
            formatted_results = []
            for i, res in enumerate(results):
                source = res.get("filename", "Unknown Source")
                content = res.get("content", "")
                score = res.get("score", 0.0)
                formatted_results.append(f"--- Result {i+1} (Source: {source}, Score: {score:.2f}) ---\n{content}\n")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"SearchQuantLibraryTool error: {e}")
            return f"Error searching quant library: {str(e)}"

class ListLibraryBooksTool(BaseTool):
    name: str = "list_library_books"
    description: str = (
        "Lists all quantitative books, research papers, and guides currently available in the AI library. "
        "Includes metadata like titles, authors, and ingestion status. "
        "Use this to discover what knowledge is available before performing a search."
    )

    async def run_tool(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        import httpx
        from app.core.config import settings
        
        try:
            # We call the internal list API
            url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/ai/library/list"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if not data:
                        return "The library is currently empty."
                    
                    report = ["### 📚 Available Library Books:"]
                    for book in data:
                        title = book.get("title") or "Unknown Title"
                        author = book.get("author") or "Unknown Author"
                        filename = book.get("filename")
                        status = book.get("status")
                        report.append(f"- **{title}** by {author} (File: `{filename}`, Status: {status})")
                    
                    return "\n".join(report)
                else:
                    return f"Failed to list library books: {resp.status_code}"
        except Exception as e:
            logger.error(f"ListLibraryBooksTool error: {e}")
            return f"Error listing library books: {str(e)}"
