from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Import Analysis Logic
from app.analysis.market_regime import get_market_context
from app.indicators.piv import calculate_n_bands, calculate_piv_levels
from app.indicators.garch_engine import garch_engine
from app.indicators.volatility import calculate_atr

# Import DB/Data Utilities
from app.backtest import fetch_data_from_db
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.database import SessionLocal
from app.utils.helpers import sanitize_numeric_dict
from app.utils.data_resolver import resolve_source_for_fund

router = APIRouter(
    prefix="/market",
    tags=["Strategy Analysis"]
)

# Dependency for DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegimeRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    bias: str = "NEUTRAL"
    fund_id: Optional[str] = None

from app.utils.market_data import fetch_candles_logic

@router.post("/regime")
async def check_market_regime_endpoint(
    req: RegimeRequest, 
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Returns the Market Regime with Institutional Data Isolation.
    """
    # Default user for local testing if header is missing
    user_id = x_user_id or "demo1"
    
    # 1. Fetch Data
    df = await fetch_candles_logic(db, req.symbol, req.timeframe, user_id, req.fund_id, limit=200)
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {req.symbol} {req.timeframe}")
        
    # 2. Analyze
    context = get_market_context(df, req.bias)
    
    # 3. Augment with input info
    context["meta"]["timeframe"] = req.timeframe
    context["meta"]["fund_id"] = req.fund_id
    
    return sanitize_numeric_dict(context)

@router.post("/volatility/piv")
async def get_piv_analysis(
    req: RegimeRequest, 
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Returns PIV analysis with Institutional Data Isolation.
    """
    user_id = x_user_id or "demo1"
    symbol = req.symbol
    timeframe = req.timeframe or "H1"
    
    # Timeframe Hierarchy Mapping
    tf_setup = {
        "M1": "M5",
        "M5": "M15",
        "M15": "H1",
        "H1": "H4",
        "H4": "D1"
    }.get(timeframe, "H4")
        
    try:
        # Fetch data for both primary and setup timeframes
        df_primary = await fetch_candles_logic(db, symbol, timeframe, user_id, req.fund_id, limit=100)
        df_setup = await fetch_candles_logic(db, symbol, tf_setup, user_id, req.fund_id, limit=200)
        
        if df_primary.empty or df_setup.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol} on {timeframe}/{tf_setup}")

        # 1. Projected Volatility
        returns = df_setup['close'].pct_change().dropna()
        proj_vol = garch_engine.get_projected_volatility(returns)
        
        # 2. Daily N-Bands
        bands = calculate_n_bands(df_primary, multiplier=1.5, gvz=proj_vol)
        
        # 3. Structural Levels
        piv_levels = calculate_piv_levels(df_setup.tail(100), gvz=proj_vol)
        piv_levels = sorted(list(set(np.round(piv_levels, 2).tolist())))

        context = {
            "symbol": symbol,
            "projected_volatility": float(proj_vol),
            "current_price": float(df_primary['close'].iloc[-1]),
            "n_bands": bands,
            "piv_levels": piv_levels,
            "volatility_regime": "High" if proj_vol > 25 else "Normal" if proj_vol > 15 else "Low",
            "meta": {
                "primary_tf": timeframe,
                "setup_tf": tf_setup,
                "fund_id": req.fund_id
            }
        }
        
        return sanitize_numeric_dict(context)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
