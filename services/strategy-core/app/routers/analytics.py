from fastapi import APIRouter, HTTPException, Query
from app.quant.analytics import analytics_engine
from app.market_data import market_data_manager
from app.schemas import (
    APIResponse_VolatilityMetrics, 
    APIResponse_VaRMetrics, 
    APIResponse_FactorExposures, 
    APIResponse_DrawdownMetrics
)
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def success_response(data: any):
    return {
        "status": "success",
        "data": data,
        "timestamp": datetime.now(timezone.utc)
    }

@router.get("/volatility", response_model=APIResponse_VolatilityMetrics)
async def get_volatility(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        market_data_manager.load_history(symbol, limit=max(limit, 1000))
        data = analytics_engine.get_volatility_metrics(symbol, timeframe, limit)
        return success_response(data)
    except Exception as e:
        logger.error(f"Quant Analytics Volatility Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/var", response_model=APIResponse_VaRMetrics)
async def get_var(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        market_data_manager.load_history(symbol, limit=max(limit, 1000))
        data = analytics_engine.get_var_metrics(symbol, timeframe, limit)
        return success_response(data)
    except Exception as e:
        logger.error(f"Quant Analytics VaR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/factors", response_model=APIResponse_FactorExposures)
async def get_factors(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        market_data_manager.load_history(symbol, limit=max(limit, 1000))
        data = analytics_engine.get_factor_exposures(symbol, timeframe, limit)
        return success_response(data)
    except Exception as e:
        logger.error(f"Quant Analytics Factors Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drawdown", response_model=APIResponse_DrawdownMetrics)
async def get_drawdown(
    symbol: str = Query(..., description="Trading symbol (e.g., XAUUSD)"),
    timeframe: str = Query("H1", description="Timeframe (e.g., M15, H1, H4)"),
    limit: int = Query(500, description="Number of candles to analyze")
):
    try:
        market_data_manager.load_history(symbol, limit=max(limit, 1000))
        data = analytics_engine.get_drawdown_metrics(symbol, timeframe, limit)
        return success_response(data)
    except Exception as e:
        logger.error(f"Quant Analytics Drawdown Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
