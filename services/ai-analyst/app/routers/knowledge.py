from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging
from app.utils.response import success_response
from app.core.globals import services

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/knowledge/context")
async def get_knowledge_context(
    symbol: str = Query(..., description="The symbol to query semantic context for"),
    include_score: bool = Query(True, description="Whether to include knowledge-driven multiplier")
):
    """
    Retrieve semantic context and knowledge score for a specific symbol/instrument.
    Integrates with FalkorDB to provide Knowledge Graph insights.
    """
    falkor = services.get("falkor")
    if not falkor:
        raise HTTPException(status_code=503, detail="FalkorService not initialized")
        
    try:
        # 1. Fetch from FalkorDB
        context = await falkor.query_context(symbol)
        
        # 2. Optionally calculate score
        if include_score:
            score = await falkor.get_knowledge_score(symbol, context)
            context["knowledge_score"] = score
        else:
            context["knowledge_score"] = 1.0
            
        return success_response(data=context)
    except Exception as e:
        logger.error(f"Failed to fetch knowledge context for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
