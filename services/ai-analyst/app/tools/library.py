from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.services.rag import RAGService
import logging

logger = logging.getLogger(__name__)

class LibrarySearchInput(BaseModel):
    query: str = Field(description="The semantic search query to find relevant information in the quantitative trading library.")
    limit: int = Field(default=5, description="Number of relevant chunks to retrieve.")

class SearchQuantLibraryTool(BaseTool):
    name: str = "search_quant_library"
    description: str = (
        "Searches institutional-grade quantitative trading books, research, and technical guides. "
        "Use this for understanding Smart Money Concepts (SMC), risk management theories (Kelly, etc.), "
        "and advanced market mechanics to build or refine strategies."
    )
    args_schema: Any = LibrarySearchInput
    rag_service: Any = Field(exclude=True) # Runtime dependency

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        query = ""
        limit = 5
        
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
            limit = input_data.get("limit", 5)
        elif isinstance(input_data, str):
            query = input_data
            
        if not query:
            return "No search query provided."

        try:
            # search_library returns list[dict] with 'content', 'score', 'filename'
            results = await self.rag_service.search_library(
                query=query,
                limit=limit,
                expand_context=True
            )
            
            if not results:
                return f"No relevant information found in the quant library for: '{query}'"
            
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
