from fastapi import FastAPI, HTTPException
from app.schemas import IndicatorRequest, IndicatorResponse, ATRRequest
from app.indicators import calculate_ema, calculate_atr
import pandas as pd
import numpy as np

app = FastAPI(title="Strategy Core Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "strategy-core"}

@app.post("/calculate/ema", response_model=IndicatorResponse)
def get_ema(req: IndicatorRequest):
    try:
        data = pd.Series(req.data)
        span = req.params.get("span", 14)
        ema = calculate_ema(data, span=span)
        # Replace NaN and Inf with None for JSON serialization
        values = ema.replace([np.inf, -np.inf], np.nan).where(pd.notnull(ema), None).tolist()
        return IndicatorResponse(values=values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate/atr", response_model=IndicatorResponse)
def get_atr(req: ATRRequest):
    try:
        high = pd.Series(req.high)
        low = pd.Series(req.low)
        close = pd.Series(req.close)
        window = req.window
        
        if not (len(high) == len(low) == len(close)):
            raise HTTPException(status_code=400, detail="Input lists must have the same length")
            
        atr = calculate_atr(high, low, close, window=window)
        
        # Convert to list and handle NaN/Inf manually to be safe
        values = []
        for val in atr:
            if pd.isna(val) or np.isinf(val):
                values.append(None)
            else:
                values.append(float(val))
                
        return IndicatorResponse(values=values)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
