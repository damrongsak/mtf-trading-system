from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import pandas as pd

from app.database import get_db
from app.models.open_interest import OpenInterest
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer, GammaLevel, MarketRegime
from app.indicators.smc import analyze_smc
from .market import fetch_candles_logic

router = APIRouter(
    prefix="/analysis/gamma",
    tags=["Gamma Analysis"]
)

class GammaLevelResponse(BaseModel):
    price: float
    strike: float
    type: str
    zone_type: str
    strength: float
    description: str
    dte: Optional[int] = None
    confluence: List[str] = []

class MarketRegimeResponse(BaseModel):
    net_gex: float
    regime: str
    gamma_flip_level: Optional[float]
    summary: str

class GammaAnalysisResponse(BaseModel):
    snapshot_at: datetime
    underlying_price: Optional[float]
    levels: List[GammaLevelResponse]
    regime: MarketRegimeResponse

@router.get("/levels", response_model=GammaAnalysisResponse)
async def get_gamma_levels(
    symbol: str = "XAUUSD", 
    current_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get the latest Gamma Levels and Market Regime.
    """
    # 1. Fetch latest snapshot time for symbol
    # Note: open_interest table stores contract_symbol but we might need to map XAUUSD to futures symbol?
    # For now, we assume the caller knows the symbol or we default to looking for anything recent.
    # The current system stores records with 'contract_symbol' like 'GCG4' or similar.
    # But usually we query by snapshot time.
    
    # Let's find the latest snapshot first
    latest_snapshot = db.query(OpenInterest.snapshot_at).order_by(OpenInterest.snapshot_at.desc()).first()
    
    if not latest_snapshot:
        raise HTTPException(status_code=404, detail="No Open Interest data found")
        
    snapshot_time = latest_snapshot[0]
    
    # 2. Fetch all records for this snapshot
    records = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_time).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="No records found for latest snapshot")
        
    # Convert to list of dicts
    data = []
    snapshot_underlying = None
    for r in records:
        data.append({
            'strike': float(r.strike),
            'call_oi': float(r.call_oi or 0),
            'put_oi': float(r.put_oi or 0),
            'underlying_price': float(r.underlying_price) if r.underlying_price else None
        })
        if r.underlying_price:
            snapshot_underlying = float(r.underlying_price)
            
    # 3. Determine 'current' price for analysis
    # Strategy: 
    # - If 'current_price' provided, use it.
    # - Else if snapshot has underlying, use it.
    # - Else fail or return error (offset calc impossible without price)
    
    price_to_use = current_price if current_price else snapshot_underlying
    
    if not price_to_use:
        # Without price, we can still return levels based on strikes, but regime might be wrong
        # Default to 0 or handle gracefully?
        price_to_use = 0.0 

    # 4. Fetch SMC Data for Confluence
    # We fetch H1 candles typically for institutional levels
    smc_data = None
    try:
        df = await fetch_candles_logic(symbol, "H1", limit=200)
        if not df.empty:
            smc_data = analyze_smc(df, symbol=symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch SMC confluence: {e}")

    # 5. Analyze
    analyzer = LiquidityProfileAnalyzer()
    # For now, if we can't get SMC easily in this sync context, we skip confluence or make it async
    result = analyzer.analyze_snapshot(data, current_spot_price=price_to_use, smc_data=smc_data)
    
    return {
        "snapshot_at": snapshot_time,
        "underlying_price": snapshot_underlying,
        "levels": result['levels'],
        "regime": result['regime']
    }
