from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    QuantAnalyzeRequest, QuantSizingRequest, 
    QuantAnalyzeResponse, QuantSizingResponse
)
from app.quant.engine import quant_engine
from app.market_data import market_data_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", response_model=QuantAnalyzeResponse)
async def analyze_market(request: QuantAnalyzeRequest):
    """
    Returns the Risk Map analysis for a given symbol and timeframe.
    """
    try:
        # Fetch candles from the manager
        df = market_data_manager.get_candles(
            symbol=request.symbol, 
            timeframe=request.timeframe, 
            limit=request.limit
        )
        
        if df.empty:
            # Try to hydrate if missing. Load more M1 candles for higher timeframes.
            hydration_limit = max(3000, request.limit * 60 if "H" in request.timeframe else request.limit)
            market_data_manager.load_history(request.symbol, limit=hydration_limit)
            df = market_data_manager.get_candles(
                symbol=request.symbol, 
                timeframe=request.timeframe, 
                limit=request.limit
            )
            
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {request.symbol}")

        result = quant_engine.analyze(request.symbol, df, request.timeframe)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        logger.error(f"Quant Analyze Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/size", response_model=QuantSizingResponse)
async def calculate_sizing(request: QuantSizingRequest):
    """
    Returns institutional-grade position sizing based on Risk Map.
    """
    try:
        df = market_data_manager.get_candles(
            symbol=request.symbol, 
            timeframe=request.timeframe, 
            limit=request.limit
        )
        
        if df.empty:
            # Load more M1 candles for higher timeframes (3000 M1 = 50 H1)
            hydration_limit = max(3000, request.limit * 60 if "H" in request.timeframe else request.limit)
            market_data_manager.load_history(request.symbol, limit=hydration_limit)
            df = market_data_manager.get_candles(
                symbol=request.symbol, 
                timeframe=request.timeframe, 
                limit=request.limit
            )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {request.symbol}")

        result = quant_engine.calculate_sizing(
            symbol=request.symbol,
            df=df,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            equity=request.equity,
            strategy_id=request.strategy_id,
            timeframe=request.timeframe
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        logger.error(f"Quant Sizing Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
