from fastapi import APIRouter, HTTPException, Query
from app.services.rag import RAGService
from app.utils.response import success_response
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
rag_service = RAGService()

class ExternalSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    partner_id: Optional[str] = None

@router.post("/search")
async def external_search(request: ExternalSearchRequest):
    """
    Scoped search for 3rd-party consumers.
    Limits metadata visibility for security and provides a simplified hit structure.
    """
    try:
        # Perform RAG Search
        raw_results = await rag_service.search_library(
            query=request.query,
            limit=request.limit or 5,
            expand_context=False # Don't expand context for external hits (save resources)
        )
        
        # Simplify hits for partner consumption
        partner_hits = []
        for hit in raw_results:
            partner_hits.append({
                "content": hit["content"],
                "score": hit["score"],
                "source": hit["filename"]
            })
            
        return success_response(
            data=partner_hits,
            message=f"Search completed for partner '{request.partner_id or 'anonymous'}'"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"External search failed: {str(e)}")
