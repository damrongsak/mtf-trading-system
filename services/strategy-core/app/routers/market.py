from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime

# Import Analysis Logic
from app.analysis.market_regime import get_market_context

# Import DB/Data Utilities
from app.backtest import fetch_data_from_db
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.database import SessionLocal
from app.utils.helpers import sanitize_numeric_dict

router = APIRouter(
    prefix="/market",
    tags=["Startgy Analysis"]
)

class RegimeRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    bias: str = "NEUTRAL"

async def fetch_candles_logic(symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    """
    Helper to fetch candles from DB.
    """
    db = SessionLocal()
    try:
        # Flexible symbol matching
        target_symbol = symbol
        data_source = "CTRADER" # Default
        
        query = db.query(MarketSymbol).join(DataSource).filter(
            (MarketSymbol.symbol == target_symbol) | (MarketSymbol.symbol == target_symbol.replace("/", "_")),
            DataSource.name == data_source
        )
        ms = query.first()
        
        if not ms:
            return pd.DataFrame()
            
        market_symbol_id = ms.id
        
        # Calculate start date based on limit roughly
        # This is an approximation, better to fetch by count if DB supports it or fetch ample time
        # H1 * 200 = 200 hours ~ 8 days
        # M15 * 200 = 50 hours ~ 2 days
        days = 30 # Fetch enough
        start_dt = datetime.utcnow() - pd.Timedelta(days=days)
        end_dt = datetime.utcnow()
        
        df = fetch_data_from_db(
            market_symbol_id=market_symbol_id, 
            timeframe=timeframe, 
            start_date=start_dt, 
            end_date=end_dt
        )
        
        if df.empty:
            return pd.DataFrame()
            
        # Limit to last N
        if len(df) > limit:
            df = df.iloc[-limit:]
            
        return df
    finally:
        db.close()

@router.post("/regime")
async def check_market_regime_endpoint(req: RegimeRequest):
    """
    Returns the Market Regime, Fakeout Status, and Dynamic Risk.
    INPUT: Symbol, Timeframe (e.g. 'H1', 'M15', 'H4')
    """
    # 1. Fetch Data
    df = await fetch_candles_logic(req.symbol, req.timeframe, limit=200)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {req.symbol} {req.timeframe}")
        
    # 2. Analyze
    context = get_market_context(df, req.bias)
    
    # 3. Augment with input info
    context["meta"]["timeframe"] = req.timeframe
    
    return sanitize_numeric_dict(context)
