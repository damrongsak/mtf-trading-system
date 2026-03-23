from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import pandas as pd
import logging

from app.schemas.risk import CorrelationRequest, CorrelationResponse
from app.services.risk_engine import RiskEngine
from app.utils.response import success_response

router = APIRouter()
logger = logging.getLogger(__name__)
risk_engine = RiskEngine()

@router.post("/risk/correlation", response_model=CorrelationResponse)
async def calculate_risk_correlation(request: CorrelationRequest):
    """
    Calculate PCA-based cross-asset correlation from price history.
    """
    try:
        # Convert dict to DataFrame
        # symbols as columns, indices as observations
        df = pd.DataFrame(request.prices)
        
        if df.empty or len(df.columns) < 2:
            raise HTTPException(status_code=400, detail="At least 2 symbols with price data required.")
            
        result = risk_engine.calculate_eigen_risk(df, threshold=request.threshold)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("reason", "PCA calculation failed"))
            
        return result
        
    except Exception as e:
        logger.error(f"Correlation API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
