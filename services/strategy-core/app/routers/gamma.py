from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import pandas as pd
import os
import json
import logging
import asyncio
import redis.asyncio as redis
from dataclasses import asdict

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
    db: Session = Depends(get_db)
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
    cache_key = f"gamma_analysis:{symbol}:{snapshot_time.isoformat()}:{price_to_use}"
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = None
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            await redis_client.close()
            return json.loads(cached_result)
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")

    # 4. Database Query Pushdown (Filter DB side instead of fetching all)
    max_call_record = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_time).order_by(OpenInterest.call_oi.desc()).first()
    max_put_record = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_time).order_by(OpenInterest.put_oi.desc()).first()
    
    filter_range = 300.0
    filtered_records = db.query(OpenInterest).filter(
        OpenInterest.snapshot_at == snapshot_time,
        OpenInterest.strike >= price_to_use - filter_range,
        OpenInterest.strike <= price_to_use + filter_range
    ).all()

    if not filtered_records and not max_call_record:
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
            'underlying_price': float(r.underlying_price) if r.underlying_price else None
        })

    # 5. Decoupled SMC Data Fetching (Graceful Fallback)
    smc_data = None
    try:
        # Wrap in timeout to prevent blocking if provider is slow
        df = await asyncio.wait_for(fetch_candles_logic(symbol, "H1", limit=200), timeout=2.0)
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
    if redis_client:
        try:
            await redis_client.setex(cache_key, 900, json.dumps(response_data, cls=NpEncoder))
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")
        finally:
            await redis_client.close()

    return response_data
