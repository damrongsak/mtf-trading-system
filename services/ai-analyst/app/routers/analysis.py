from fastapi import APIRouter, HTTPException, Header
import traceback
from datetime import datetime, timezone

from app.schemas.analysis import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.utils.response import success_response
from pydantic import BaseModel

# We need access to the services. 
from app.core.globals import services

router = APIRouter(
    prefix="/analyze",  # Mounted under /api/v1
    tags=["Analysis"]
)

class SMCNarrativeRequest(BaseModel):
    smc_data: dict
    price_context: dict

@router.post("/market", response_model=AnalysisResponse)
async def analyze_market(request: MarketAnalysisRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")
    
    context = request.model_dump()
    insight = await services["gemini"].generate_market_outlook(context)
    
    # Return directly to match AnalysisResponse schema (no nesting)
    return {
        "status": "success",
        "insight": insight,
        "message": "Operation completed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/journal", response_model=AnalysisResponse)
async def analyze_journal(request: JournalAnalysisRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")

    # RAG Step: Find similar entries
    similar_entries = []
    if services["rag"]:
        try:
            # Legacy method call, ensuring compatibility if rag.py changed
            similar_entries = await services["rag"].search_similar_entries(request.entry_content, user_id=request.user_id)
        except Exception as e:
             print(f"RAG search failed: {e}")

    insight = await services["gemini"].analyze_journal_entry(request.entry_content, similar_entries, user_id=request.user_id)
    
    # Return directly to match AnalysisResponse schema
    return {
        "status": "success",
        "insight": insight,
        "message": "Operation completed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/smc-narrative", response_model=AnalysisResponse)
async def analyze_smc_narrative(request: SMCNarrativeRequest):
    if not services["gemini"]:
        raise HTTPException(status_code=503, detail="AI Service unavailable")
    
    insight = await services["gemini"].generate_smc_narrative(request.smc_data, request.price_context)
    
    # Return directly to match AnalysisResponse schema
    return {
        "status": "success",
        "insight": insight,
        "message": "Operation completed successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

class AnalysisRequest(BaseModel):
    symbol: str = "XAU/USD"
    context: str = ""

@router.post("/sentiment")
async def analyze_sentiment(req: AnalysisRequest):
    if not services["sentiment"]:
        raise HTTPException(status_code=503, detail="Sentiment Service unavailable")
    res = await services["sentiment"].get_sentiment(req.symbol)
    return success_response(data=res)
