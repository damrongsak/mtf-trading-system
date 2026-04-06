from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel
import pandas as pd
import os
import json
import logging
import asyncio
from dataclasses import asdict
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.open_interest import OpenInterest
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer, GammaLevel, MarketRegime
from app.indicators.smc import analyze_smc
from .market import fetch_candles_logic

router = APIRouter(
    prefix="/analysis/gamma",
    tags=["Gamma Analysis"]
)

def get_fetch_candles():
    return fetch_candles_logic

class GammaLevelResponse(BaseModel):
    price: float
    strike: float
    type: str
    zone_type: str
    strength: float
    description: str
    dte: Optional[int] = None
    term: Optional[str] = None
    market_action: Optional[str] = None
    zone_type_v2: Optional[str] = None
    significance_score: Optional[float] = None
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
    max_pain: float
    mapped_max_pain: float
    heatmap: List[dict]

@router.get("/levels", response_model=GammaAnalysisResponse)
async def get_gamma_levels(
    symbol: str = "XAUUSD", 
    snapshot_at: Optional[datetime] = None,
    current_price: Optional[float] = None,
    min_dte: Optional[int] = None,
    max_dte: Optional[int] = None,
    fund_id: Optional[str] = None,
    db: Session = Depends(get_db),
    fetch_candles: Any = Depends(get_fetch_candles),
    x_user_id: Optional[str] = Header(None)
):
    """
    Get the latest Gamma Levels and Market Regime.
    """
    # 1. Determine snapshot time
    if snapshot_at:
        snapshot_time = snapshot_at
    else:
        # Find latest snapshot for SPECIFIC symbol mapping
        # In this system, contract_symbol might be GCG4 (Gold) etc.
        # But we mostly care about the primary asset data.
        # If symbol is XAUUSD, we look for anything that maps to it or just the latest global OI if symbol isn't contract-specific.
        latest_snapshot = db.query(OpenInterest.snapshot_at)\
            .order_by(OpenInterest.snapshot_at.desc())\
            .first()
        
        if not latest_snapshot:
            raise HTTPException(status_code=404, detail="No Open Interest data found")
        snapshot_time = latest_snapshot[0]
    
    # 2. Determine base price for filtering and cache key
    snapshot_underlying = None
    if not current_price:
        usd_rec = db.query(OpenInterest.underlying_price).filter(
            OpenInterest.snapshot_at == snapshot_time,
            OpenInterest.underlying_price.isnot(None)
        ).first()
        if usd_rec:
            snapshot_underlying = float(usd_rec[0])

    price_to_use = current_price if current_price else snapshot_underlying
    if not price_to_use:
        price_to_use = 0.0

    # 3. Redis Caching
    cache_key = f"gamma_analysis:{symbol}:{snapshot_time.isoformat()}:{price_to_use}:{min_dte}:{max_dte}"
    try:
        redis_client = get_redis_client()
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")

    # 4. Database Query Pushdown (Filter DB side instead of fetching all)
    base_filter = [OpenInterest.snapshot_at == snapshot_time]
    if min_dte is not None:
        base_filter.append(OpenInterest.dte >= min_dte)
    if max_dte is not None:
        base_filter.append(OpenInterest.dte <= max_dte)

    # Resolve Basis for Filtering
    # If price_to_use is spot (~2350) and DB strikes are ~4800, we must adjust filter
    db_underlying = snapshot_underlying or price_to_use
    basis_adj = 0.0
    if price_to_use > 0 and db_underlying > 0:
        # If divergence is > 30% it's likely a scaling difference
        if abs(db_underlying - price_to_use) / price_to_use > 0.3:
            basis_adj = db_underlying - price_to_use
    
    # Strikes to fetch - centered around the adjusted spot
    fetch_center = price_to_use + basis_adj
    filter_range = 2000.0 # Catch major institutional walls (e.g. 4000, 6000)
    
    max_call_record = db.query(OpenInterest).filter(*base_filter).order_by(OpenInterest.call_oi.desc()).first()
    max_put_record = db.query(OpenInterest).filter(*base_filter).order_by(OpenInterest.put_oi.desc()).first()
    
    filtered_records = db.query(OpenInterest).filter(
        *base_filter,
        OpenInterest.strike >= fetch_center - filter_range,
        OpenInterest.strike <= fetch_center + filter_range
    ).all()

    if not filtered_records and not max_call_record:
        # Fallback: if no records near spot, just use global maxes
        if max_call_record or max_put_record:
            filtered_records = []
        else:
            if redis_client: await redis_client.close()
            raise HTTPException(status_code=404, detail="No records found for specified parameters")

    combined_records_dict = {}
    if max_call_record: combined_records_dict[max_call_record.id] = max_call_record
    if max_put_record: combined_records_dict[max_put_record.id] = max_put_record
    for r in filtered_records:
        combined_records_dict[r.id] = r

    data = []
    for r in combined_records_dict.values():
        data.append({
            'strike': float(r.strike),
            'call_oi': float(r.call_oi or 0),
            'put_oi': float(r.put_oi or 0),
            'dte': r.dte,
            'contract_symbol': r.contract_symbol,
            'underlying_price': float(r.underlying_price) if r.underlying_price else None
        })

    # 5. Decoupled SMC Data Fetching (Graceful Fallback)
    smc_data = None
    try:
        # Wrap in timeout to prevent blocking if provider is slow
        user_context_id = x_user_id or "demo1"
        df, _ = await asyncio.wait_for(fetch_candles(db, symbol, "H1", user_context_id, fund_id, limit=200), timeout=2.0)
        if not df.empty:
            smc_data = analyze_smc(df, symbol=symbol)
    except Exception as e:
        logger.warning(f"SMC data fallback used due to timeout/error: {e}")

    # 6. Analyze
    analyzer = LiquidityProfileAnalyzer()
    result = analyzer.analyze_snapshot(data, current_spot_price=price_to_use, smc_data=smc_data)
    
    response_data = {
        "snapshot_at": snapshot_time.isoformat(),
        "underlying_price": snapshot_underlying,
        "levels": [asdict(l) for l in result.get('levels', [])],
        "regime": asdict(result['regime']) if 'regime' in result else {},
        "max_pain": result.get('max_pain', 0.0),
        "mapped_max_pain": result.get('mapped_max_pain', 0.0),
        "heatmap": result.get('heatmap', [])
    }

    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super(NpEncoder, self).default(obj)

    # 7. Write to Cache (15 min TTL)
    try:
        redis_client = get_redis_client()
        await redis_client.setex(cache_key, 900, json.dumps(response_data, cls=NpEncoder))
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")

    return response_data
