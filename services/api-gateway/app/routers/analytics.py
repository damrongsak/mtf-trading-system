from fastapi import APIRouter, HTTPException, Query
from app.services.internal_client import strategy_client
from app.schemas.generated import (
    APIResponseVolatilityMetrics,
    APIResponseVaRMetrics,
    APIResponseFactorExposures,
    APIResponseDrawdownMetrics
)
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
