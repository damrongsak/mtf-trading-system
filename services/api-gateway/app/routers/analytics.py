from fastapi import APIRouter, HTTPException, Query
from app.services.internal_client import strategy_client
from app.schemas.generated import (
    APIResponseVolatilityMetrics,
    APIResponseVaRMetrics,
    APIResponseFactorExposures,
    APIResponseDrawdownMetrics
)
from app.schemas.analytics import (
    LatencyHeatmapResponse,
    PerformanceComparisonResponse,
    ExecutionRejectionResponse,
    LatencyBucket,
    PerformanceComparisonItem,
    RejectionReasonSummary,
    AccountHistoryResponse,
    AccountHistoryItem,
    HRPWeightsResponse,
    DriftAlert,
    DriftAlertsResponse
)
from app.models.account_history import AccountHistory
from uuid import UUID
from datetime import datetime
from app.utils.cache import execution_cache
import json
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select
from app.models.trade import Trade
from app.models.signal_log import SignalLog
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)

@router.get("/volatility", response_model=APIResponseVolatilityMetrics)
async def get_volatility(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        return await strategy_client.get_volatility(symbol, timeframe, limit)
    except Exception as e:
        logger.error(f"Gateway Analytics Volatility Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/var", response_model=APIResponseVaRMetrics)
async def get_var(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        return await strategy_client.get_var(symbol, timeframe, limit)
    except Exception as e:
        logger.error(f"Gateway Analytics VaR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/factors", response_model=APIResponseFactorExposures)
async def get_factors(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        return await strategy_client.get_factors(symbol, timeframe, limit)
    except Exception as e:
        logger.error(f"Gateway Analytics Factors Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drawdown", response_model=APIResponseDrawdownMetrics)
async def get_drawdown(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        return await strategy_client.get_drawdown(symbol, timeframe, limit)
    except Exception as e:
        logger.error(f"Gateway Analytics Drawdown Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latency/heatmap", response_model=LatencyHeatmapResponse)
async def get_latency_heatmap(db: Session = Depends(get_db)):
    """
    Returns aggregated latency data bucketed by Hour of Day and Symbol.
    """
    try:
        # PostgreSQL syntax for extract hour
        hour_col = func.extract('hour', Trade.signal_timestamp).label('hour')
        
        query = db.query(
            hour_col,
            Trade.symbol,
            func.avg(Trade.latency_ms).label('avg_latency'),
            func.min(Trade.latency_ms).label('min_latency'),
            func.max(Trade.latency_ms).label('max_latency'),
            func.count(Trade.trade_id).label('count')
        ).filter(Trade.latency_ms.is_not(None))\
         .group_by(hour_col, Trade.symbol).all()
        
        buckets = [
            LatencyBucket(
                hour=int(r.hour),
                symbol=r.symbol,
                avg_latency_ms=float(r.avg_latency),
                min_latency_ms=float(r.min_latency),
                max_latency_ms=float(r.max_latency),
                count=r.count
            ) for r in query
        ]
        return LatencyHeatmapResponse(buckets=buckets)
    except Exception as e:
        logger.error(f"Latency Heatmap Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch latency heatmap: {str(e)}")

@router.get("/performance/comparison", response_model=PerformanceComparisonResponse)
async def get_performance_comparison(db: Session = Depends(get_db)):
    """
    Compares P&L for signals that were executed both as Shadow and Live.
    """
    try:
        # Find signals that have both shadow and live trades
        # join trades on itself by signal_id
        shadow = select(Trade).where(Trade.is_shadow == True).alias('shadow')
        live = select(Trade).where(Trade.is_shadow == False).alias('live')
        
        stmt = select(
            shadow.c.signal_id,
            shadow.c.symbol,
            shadow.c.pnl_usd.label('shadow_pnl'),
            live.c.pnl_usd.label('live_pnl'),
            shadow.c.latency_ms.label('shadow_latency'),
            live.c.latency_ms.label('live_latency')
        ).join(live, shadow.c.signal_id == live.c.signal_id)
        
        results = db.execute(stmt).all()
        
        comparisons = []
        for r in results:
            slippage = (r.live_pnl - r.shadow_pnl) if (r.live_pnl is not None and r.shadow_pnl is not None) else None
            lat_gap = (r.live_latency - r.shadow_latency) if (r.live_latency is not None and r.shadow_latency is not None) else None
            
            comparisons.append(PerformanceComparisonItem(
                signal_id=r.signal_id,
                symbol=r.symbol,
                live_pnl=float(r.live_pnl) if r.live_pnl is not None else None,
                shadow_pnl=float(r.shadow_pnl) if r.shadow_pnl is not None else None,
                slippage_usd=float(slippage) if slippage is not None else None,
                latency_gap_ms=float(lat_gap) if lat_gap is not None else None
            ))
            
        return PerformanceComparisonResponse(comparisons=comparisons)
    except Exception as e:
        logger.error(f"Performance Comparison Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance comparison: {str(e)}")

@router.get("/execution/rejections", response_model=ExecutionRejectionResponse)
async def get_execution_rejections(db: Session = Depends(get_db)):
    """
    Summarizes rejection reasons from SignalLog.
    """
    try:
        rejections = db.query(
            SignalLog.reason,
            func.count(SignalLog.id).label('count'),
            func.max(SignalLog.timestamp).label('latest_at')
        ).filter(SignalLog.status == 'REJECTED')\
         .group_by(SignalLog.reason).all()
        
        total = sum(r.count for r in rejections)
        
        items = [
            RejectionReasonSummary(
                reason=r.reason or "Unknown",
                count=r.count,
                latest_at=r.latest_at
            ) for r in rejections
        ]
        
        return ExecutionRejectionResponse(
            rejections=items,
            total_rejections=total
        )
    except Exception as e:
        logger.error(f"Execution Rejections Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch execution rejections: {str(e)}")

@router.get("/accounts/{account_id}/history", response_model=AccountHistoryResponse)
async def get_account_history(
    account_id: UUID,
    limit: int = Query(100, description="Number of snapshots to return"),
    db: Session = Depends(get_db)
):
    """
    Returns time-series history for a specific broker account.
    """
    try:
        history = db.query(AccountHistory)\
            .filter(AccountHistory.broker_account_id == account_id)\
            .order_by(AccountHistory.timestamp.desc())\
            .limit(limit).all()
        
        items = [
            AccountHistoryItem(
                id=h.id,
                broker_account_id=h.broker_account_id,
                balance=float(h.balance),
                equity=float(h.equity),
                used_margin=float(h.used_margin),
                free_margin=float(h.free_margin),
                margin_level=float(h.margin_level) if h.margin_level is not None else None,
                unrealized_gross=float(h.unrealized_gross) if h.unrealized_gross is not None else None,
                unrealized_net=float(h.unrealized_net) if h.unrealized_net is not None else None,
                timestamp=h.timestamp
            ) for h in history
        ]
        
        return AccountHistoryResponse(history=items)
    except Exception as e:
        logger.error(f"Account History Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch account history: {str(e)}")

@router.get("/funds/{fund_id}/hrp-weights", response_model=HRPWeightsResponse)
async def get_hrp_weights(fund_id: UUID):
    """
    Returns current HRP/Risk Parity weights for a fund from Redis.
    """
    try:
        cache_key = f"fund:{fund_id}:risk_parity_weights"
        raw_weights = await execution_cache.redis.get(cache_key)
        
        if not raw_weights:
            # Fallback or empty response
            return HRPWeightsResponse(
                fund_id=fund_id,
                weights={},
                updated_at=datetime.utcnow()
            )
            
        weights = json.loads(raw_weights)
        return HRPWeightsResponse(
            fund_id=fund_id,
            weights=weights,
            updated_at=datetime.utcnow() # Redis doesn't store TTL as precise updated_at easily without extra metadata
        )
    except Exception as e:
        logger.error(f"HRP Weights Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch HRP weights: {str(e)}")

@router.get("/alerts/drift", response_model=DriftAlertsResponse)
async def get_drift_alerts():
    """
    Returns recent broker drift alerts from Redis Stream.
    """
    try:
        # Read last 20 messages from the drift stream
        stream_key = "system.alerts.drift"
        messages = await execution_cache.redis.xrevrange(stream_key, count=20)
        
        alerts = []
        for msg_id, payload in messages:
            try:
                data = json.loads(payload.get("payload", "{}"))
                alerts.append(DriftAlert(
                    type=data.get("type", "UNKNOWN"),
                    severity=data.get("severity", "WARNING"),
                    fund_id=data.get("fund_id"),
                    account_id=data.get("account_id"),
                    broker=data.get("broker"),
                    symbol=data.get("symbol"),
                    drift_units=data.get("drift_units"),
                    relative_drift=data.get("relative_drift"),
                    details=data.get("details"),
                    timestamp=data.get("timestamp", datetime.utcnow().isoformat())
                ))
            except Exception as ex:
                logger.error(f"Failed to parse drift alert {msg_id}: {ex}")
                
        return DriftAlertsResponse(alerts=alerts)
    except Exception as e:
        logger.error(f"Drift Alerts Error: {e}")
        # Return empty list instead of 500 if stream doesn't exist yet
        return DriftAlertsResponse(alerts=[])
