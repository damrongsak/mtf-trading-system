from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
import httpx
import os
import logging
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/news",
    tags=["news"],
    responses={404: {"description": "Not found"}},
)

DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

# Shared HTTP Client (Assuming app/main.py manages global client or we create one here)
# For simplicity, using async context manager per request or similar pattern to other routers
# But better to use shared if available. Let's use clean AsyncClient per request for now to match data.py pattern

@router.get("/headlines")
async def get_headlines(
    symbol: str = Query(..., description="Symbol to fetch news for (e.g., XAU/USD)")
):
    """
    Proxy to Data Pipeline: Get News Headlines
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/news/headlines",
                params={"symbol": symbol},
                timeout=10.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/sentiment/history")
async def get_sentiment_history(
    symbol: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Proxy to Data Pipeline: Get Sentiment History
    """
    params = {}
    if symbol: params["symbol"] = symbol
    if start_date: params["start_date"] = start_date
    if end_date: params["end_date"] = end_date
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/news/sentiment/history",
                params=params,
                timeout=10.0
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.post("/analyze")
async def trigger_analysis(
    payload: dict
):
    """
    Proxy to AI Analyst: Trigger Sentiment Analysis
    Payload: {"symbol": "XAU/USD", "context": "..."}
    """
    async with httpx.AsyncClient() as client:
        try:
            # AI Analyst endpoint: /analyze/sentiment
            response = await client.post(
                f"{AI_ANALYST_URL}/analyze/sentiment",
                json=payload,
                timeout=30.0 # Geminii can be slow
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
