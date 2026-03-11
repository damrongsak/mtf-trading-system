from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional
import httpx
import os
import logging
from datetime import datetime

from app.utils.http_client import get_internal_client

router = APIRouter(
    prefix="/api/v1/news",
    tags=["news"],
    responses={404: {"description": "Not found"}},
)

DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

@router.get("/headlines")
async def get_headlines(
    symbol: str = Query(..., description="Symbol to fetch news for (e.g., XAU/USD)"),
    count: int = Query(10, description="Number of headlines"),
    from_date: Optional[str] = Query(None, description="Start date (ISO)"),
    to_date: Optional[str] = Query(None, description="End date (ISO)")
):
    """
    Proxy to Data Pipeline: Get News Headlines
    """
    async with await get_internal_client() as client:
        try:
            params = {"symbol": symbol, "count": count}
            if from_date: params["from_date"] = from_date
            if to_date: params["to_date"] = to_date

            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/news/headlines",
                params=params,
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
    
    async with await get_internal_client() as client:
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
    async with await get_internal_client() as client:
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

@router.get("/calendar")
async def get_calendar(
    country: Optional[str] = Query(None),
    impact: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Proxy to Data Pipeline: Get Economic Calendar
    """
    params = {}
    if country: params["country"] = country
    if impact: params["impact"] = impact
    if date_from: params["date_from"] = date_from
    if date_to: params["date_to"] = date_to
    
    async with await get_internal_client() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/news/calendar",
                params=params,
                timeout=10.0
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.post("/calendar/sync")
async def sync_calendar():
    """
    Proxy to Data Pipeline: Sync Calendar
    """
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/news/calendar/sync",
                timeout=30.0
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
