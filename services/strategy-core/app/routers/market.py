from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime, timezone

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
        start_dt = datetime.now(timezone.utc) - pd.Timedelta(days=days)
        end_dt = datetime.now(timezone.utc)
        
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

@router.post("/volatility/piv")
async def get_piv_analysis(req: RegimeRequest):
    """
    Returns PIV analysis including N-Bands, VBSR levels, and GARCH forecast.
    INPUT: Symbol, Timeframe (M5, M15, H1, H4, etc.)
    """
    symbol = req.symbol
    timeframe = req.timeframe or "H1"
    
    # Logic for secondary (context) timeframe
    # M5 -> M15/H1 context
    # H1 -> H4 context
    # H4 -> Daily context
    if timeframe == "M5":
        tf_setup = "M15"
    elif timeframe == "M15":
        tf_setup = "H1"
    elif timeframe == "H1":
        tf_setup = "H4"
    elif timeframe == "H4":
        tf_setup = "D1"
    else:
        tf_setup = "H4" # Default fallback
        
    try:
        # Fetch data for both timeframes
        # Limit 100 for N-Bands/Volatility calculation
        df_primary = await fetch_candles_logic(symbol, timeframe, limit=100)
        # Limit 200 for VBSR levels / GARCH on higher timeframe
        df_setup = await fetch_candles_logic(symbol, tf_setup, limit=200)
        
        if df_primary.empty or df_setup.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol} on {timeframe}/{tf_setup}")

        # 1. Projected Volatility (GARCH / GVZ Fallback)
        returns = df_setup['close'].pct_change().dropna()
        proj_vol = garch_engine.get_projected_volatility(returns)
        
        # 2. Daily N-Bands (Calculated on primary TF for current range)
        bands = calculate_n_bands(df_primary, multiplier=1.5, gvz=proj_vol)
        
        # 3. VBSR Structural Levels (on setup TF)
        # We take latest 100 for structure finding
        piv_levels = calculate_piv_levels(df_setup.tail(100), gvz=proj_vol)
        
        # Cleanup levels: remove duplicates and sort
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
                "setup_tf": tf_setup
            }
        }
        
        return sanitize_numeric_dict(context)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
