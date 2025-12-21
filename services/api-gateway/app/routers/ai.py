from fastapi import APIRouter, HTTPException
from app.schemas.ai import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

@router.post("/market-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_market(req: MarketAnalysisRequest):
    """
    Proxy market analysis request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/analyze/market", 
                json=req.model_dump(mode='json'),
                timeout=30.0 # LLMs can be slow
            )
            response.raise_for_status()
            return success_response(data=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/journal-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_journal(req: JournalAnalysisRequest):
    """
    Proxy journal analysis request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/analyze/journal", 
                json=req.model_dump(mode='json'),
                timeout=30.0
            )
            response.raise_for_status()
            return success_response(data=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

from pydantic import BaseModel
class AgentRunRequest(BaseModel):
    input_text: str

@router.post("/agent/observer/run")
async def run_market_observer(req: AgentRunRequest):
    """
    Proxy agent run request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/agent/observer/run", 
                json=req.model_dump(),
                timeout=60.0 # Agents can be slow
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")
