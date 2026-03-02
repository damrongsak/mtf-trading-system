from fastapi import APIRouter, Depends, Query, HTTPException
import os
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.candle import Candle
from app.schemas.response import APIResponse, ResponseStatus
from app.utils.response import success_response
from pydantic import BaseModel, ConfigDict
from app.utils.symbol_utils import normalize_symbol

router = APIRouter(
    tags=["market"]
)

class CandleRes(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    model_config = ConfigDict(from_attributes=True)

@router.get("/candles", response_model=APIResponse[List[CandleRes]])
async def get_candles(
    symbol: str = Query(..., description="Symbol (e.g. EUR_USD)"),
    timeframe: str = Query(..., description="Timeframe (e.g. H1)"),
    count: int = Query(500, description="Number of candles to return"),
    from_time: Optional[datetime] = Query(None, description="Start time"),
    to_time: Optional[datetime] = Query(None, description="End time"),
    data_source: str = Query("CTRADER", description="Data Source Preference"),
    db: Session = Depends(get_db)
):
    # 1. Resolve MarketSymbol ID
    # Use flexible matching (replace slash with underscore or vice versa if needed)
    # Default to OANDA for now if not specified in deeper logic, but we exposed param.
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    
    symbol_norm = normalize_symbol(symbol)
    
    ms = db.query(MarketSymbol).join(DataSource).filter(
        (MarketSymbol.symbol == symbol_norm) | (MarketSymbol.symbol == symbol),
        DataSource.name == data_source
    ).first()
    
    if not ms:
        # If no config found, return empty or error. Empty is safer for UI.
        return APIResponse(status=ResponseStatus.SUCCESS, data=[])

    # 2. Query Candles by MarketSymbol ID
    query = db.query(Candle).filter(
        Candle.market_symbol_id == ms.id,
        Candle.timeframe == timeframe
    )

    if from_time:
        query = query.filter(Candle.timestamp >= from_time)
    if to_time:
        query = query.filter(Candle.timestamp <= to_time)
    
    # Get latest candles
    # To get "last 500", need to sort desc, limit, then maybe reverse?
    # but efficiently, we just return them. Client can reverse if needed, or we reverse.
    # Usually charts expect time ascending.
    
    candles = query.order_by(desc(Candle.timestamp)).limit(count).all()
    
    # Reverse to return oldest first
    candles.reverse()
    
    return APIResponse(
        status=ResponseStatus.SUCCESS,
        data=candles
    )

@router.get("/symbols", response_model=APIResponse[List[dict]])
async def get_market_symbols(
    data_source: str = Query("CTRADER", description="Data Source Name"),
    db: Session = Depends(get_db)
):
    """
    Get all market symbols for a given data source, including global broker details.
    """
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    
    symbols = db.query(MarketSymbol).join(DataSource).filter(
        DataSource.name == data_source,
        DataSource.is_active == True,
        MarketSymbol.is_active == True
    ).order_by(MarketSymbol.symbol).all()
    
    # Simple Dict conversion to include 'details' JSON
    # Pydantic model would be better but dict is flexible for variable JSON schemas
    data = []
    for s in symbols:
        data.append({
            "id": str(s.id),
            "symbol": s.symbol,
            "display_name": s.display_name,
            "category": s.category.name if s.category else "Other",
            "details": s.details # This is the critical new part
        })
        
    return success_response(data=data)

@router.get("/symbols/{symbol}/details")
async def get_symbol_details(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    Fetch up-to-date details for a specific symbol from the relevant Broker.
    Updates the local DB cache and returns the details.
    """
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource

    # 1. Resolve Symbol and Provider
    # We look for the OANDA one first as it's the most common for details, 
    # but the user might be asking for a CTRADER specific one.
    # Try exact match first
    ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol).first()
    
    if not ms:
        # Try normalized OANDA match (XAUUSD -> XAU/USD) if needed, 
        # but the request usually uses the exact symbol stored.
        # If not found, try replacing underscore/slash
        alt_symbol = symbol.replace("_", "/") if "_" in symbol else symbol.replace("/", "_")
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == alt_symbol).first()

    if not ms:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in database")

    source = ms.data_source
    if not source:
        raise HTTPException(status_code=400, detail="Symbol has no linked data source")

    # 2. Handle by Provider
    if source.provider == "OANDA":
        token = os.getenv("OANDA_API_TOKEN") or os.getenv("OANDA_API_KEY")
        account_id = os.getenv("OANDA_ACCOUNT_ID")
        env = os.getenv("OANDA_ENV", "practice")
        
        if not token or not account_id:
            raise HTTPException(status_code=500, detail="OANDA configuration missing (Env vars)")

        # Normalize for OANDA API (XAUUSD or XAU/USD -> XAU_USD)
        oanda_symbol = ms.symbol.replace("/", "_").replace("-", "_")
        
        host = "api-fxtrade.oanda.com" if env == "live" else "api-fxpractice.oanda.com"
        url = f"https://{host}/v3/accounts/{account_id}/instruments?instruments={oanda_symbol}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=10.0)
                
                if response.status_code != 200:
                    try:
                        detail = response.json().get("errorMessage", response.text)
                    except:
                        detail = response.text
                    raise HTTPException(status_code=response.status_code, detail=f"OANDA Error: {detail}")
                    
                data = response.json()
                instruments = data.get("instruments", [])
                
                if not instruments:
                    raise HTTPException(status_code=404, detail="Symbol not found at OANDA")
                    
                details = instruments[0]
                
                # Update DB
                ms.details = details
                db.commit()
                db.refresh(ms)
                
                return success_response(data=details)
                
            except httpx.RequestError as e:
                 raise HTTPException(status_code=503, detail=f"OANDA Connection Failed: {str(e)}")

    elif source.provider == "CTRADER":
        # For cTrader, if we have details in DB, use them. 
        # Real-time refresh from cTrader usually happens during ingestion or via Execution service.
        # For now, return what we have or a placeholder if missing.
        if ms.details:
            return success_response(data=ms.details)
        else:
             # cTrader details are usually populated via internal_client if we had an endpoint there
             # For now, return what we have as "details"
             return success_response(data={"symbol": ms.symbol, "provider": "CTRADER", "info": "Details loaded from cache"})

    else:
        # Generic fallback
        if ms.details:
            return success_response(data=ms.details)
        raise HTTPException(status_code=400, detail=f"Provider {source.provider} does not support on-demand detail refresh yet")
