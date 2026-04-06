from fastapi import APIRouter, HTTPException, Depends, Header
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    QuantAnalyzeRequest, QuantSizingRequest, 
    QuantAnalyzeResponse, QuantSizingResponse
)
from app.quant.engine import quant_engine
from app.market_data import market_data_manager
from app.utils.market_data import fetch_candles_logic
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", response_model=QuantAnalyzeResponse)
async def analyze_market(
    request: QuantAnalyzeRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Returns the Risk Map analysis for a given symbol and timeframe.
    """
    try:
        if not x_user_id:
            logger.warning("Quant Analyze Request missing X-User-Id header.")
            raise HTTPException(status_code=401, detail="X-User-Id header is required.")

        try:
            # Validate it's a valid UUID
            user_id = str(uuid.UUID(x_user_id))
        except ValueError:
            logger.error(f"Invalid UUID in X-User-Id: {x_user_id}")
            raise HTTPException(status_code=400, detail=f"Invalid X-User-Id format: {x_user_id}")

        logger.info(f"Quant Analyze Input: symbol={request.symbol}, timeframe={request.timeframe}, fund_id={request.fund_id}, user_id={user_id}")
        
        # Fetch candles using institutional logic (Unpack Tuple)
        df, source_name = await fetch_candles_logic(
            db=db,
            symbol=request.symbol,
            timeframe=request.timeframe,
            user_id=user_id,
            fund_id=request.fund_id,
            limit=request.limit
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {request.symbol} via {source_name}")

        result = quant_engine.analyze(request.symbol, df, request.timeframe)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        # Enrich with metadata
        result["context"] = result.get("context", {})
        result["context"]["data_source"] = source_name
        result["context"]["fund_id"] = request.fund_id
            
        return result
    except Exception as e:
        logger.error(f"Quant Analyze Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/size", response_model=QuantSizingResponse)
async def calculate_sizing(
    request: QuantSizingRequest,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
):
    """
    Returns institutional-grade position sizing based on Risk Map.
    """
    try:
        if not x_user_id:
            logger.warning("Quant Sizing Request missing X-User-Id header.")
            raise HTTPException(status_code=401, detail="X-User-Id header is required.")

        try:
            # Validate it's a valid UUID
            user_id = str(uuid.UUID(x_user_id))
        except ValueError:
            logger.error(f"Invalid UUID in X-User-Id: {x_user_id}")
            raise HTTPException(status_code=400, detail=f"Invalid X-User-Id format: {x_user_id}")
            
        logger.info(f"Quant Sizing Input: symbol={request.symbol}, timeframe={request.timeframe}, fund_id={request.fund_id}, user_id={user_id}")
        
        # Fetch candles using institutional logic (Unpack Tuple)
        df, source_name = await fetch_candles_logic(
            db=db,
            symbol=request.symbol,
            timeframe=request.timeframe,
            user_id=user_id,
            fund_id=request.fund_id,
            limit=request.limit
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {request.symbol} via {source_name}")

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
            
        # Enrich risk_map with metadata
        if "risk_map" in result:
            result["risk_map"]["context"] = result["risk_map"].get("context", {})
            result["risk_map"]["context"]["data_source"] = source_name
            result["risk_map"]["context"]["fund_id"] = request.fund_id
            
        return result
    except Exception as e:
        logger.error(f"Quant Sizing Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
