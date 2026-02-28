from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np
import traceback

from app.engine.expression_engine import ExpressionEngine, SecurityException
from app.backtest import fetch_data_from_db
from app.utils.helpers import resolve_market_symbol_id
from app.database import SessionLocal

router = APIRouter(prefix="/alpha", tags=["Alpha Engine"])

class AlphaRequest(BaseModel):
    formula: str
    symbol: str
    timeframe: str = "H1" # Default to H1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AlphaResponse(BaseModel):
    signal: List[Optional[float]] # The resulted time series
    metrics: Dict[str, Any] # Sharpe, IC, etc.
    timestamps: List[datetime]

@router.post("/test", response_model=AlphaResponse)
def test_alpha(req: AlphaRequest):
    return _run_alpha(req, mode="full")

@router.post("/preview", response_model=AlphaResponse)
def preview_alpha(req: AlphaRequest):
    return _run_alpha(req, mode="preview")

def _run_alpha(req: AlphaRequest, mode: str):
    db = SessionLocal()
    try:
        # 1. Resolve Symbol
        ms_id = resolve_market_symbol_id(db, req.symbol)
        if not ms_id:
             # Try default XAU_USD if not found (for dev UX)
             ms_id = resolve_market_symbol_id(db, "XAU_USD")
             if not ms_id:
                raise HTTPException(status_code=404, detail=f"Symbol {req.symbol} not found")

        # 2. Fetch Data
        # Preview mode: fetch small chunk (last 100 rows)
        # Full mode: fetch requested range or default 1000 candles
        
        limit = 100 if mode == "preview" else 2000
        
        # We use fetch_data_from_db but it handles dates. 
        # For limit we might need to slice after fetch if fetch_data doesn't support limit directly.
        # Check fetch_data_from_db implementation? It usually returns DF.
        
        df = fetch_data_from_db(
            market_symbol_id=ms_id,
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date
        )
        
        if df.empty:
            return AlphaResponse(signal=[], metrics={}, timestamps=[])

        # Slice for limit (fetch_data gets range, so we slice tail)
        if len(df) > limit:
            df = df.iloc[-limit:]
            
        # 3. Setup Context
        # Structure: Index=Timestamp, Cols=open, high, low, close, volume
        # ExpressionEngine expects separate DataFrames or Series?
        # "context: dict mapping variable names to DataFrames (e.g. {'close': df})"
        # If we have only 1 symbol, context['close'] is a Series (or single-col DF).
        # To support 'rank' properly in future, we'd need MultiIndex or Panel.
        # For single-symbol MVP, 'rank' will just return 1.0. 
        # But 'delay', 'ts_max' work fine.
        
        context = {
            'open': df['open'],
            'high': df['high'],
            'low': df['low'],
            'close': df['close'],
            'volume': df['volume']
        }
        
        # 4. Evaluate
        engine = ExpressionEngine()
        try:
            result_series = engine.evaluate(req.formula, context)
        except SecurityException as se:
             raise HTTPException(status_code=400, detail=str(se))
        except Exception as e:
             raise HTTPException(status_code=400, detail=f"Evaluation Error: {e}")

        # 5. Calculate Basic Metrics (IC, Sharpe)
        # Simplified for preview
        metrics = {}
        
        # Replace NaN and ensure float (handles boolean signals from logic ops)
        result_clean = result_series.replace([np.inf, -np.inf], np.nan).fillna(0).astype(float)
        
        # Calculate Returns
        # Simple strategy: If signal > 0 buy, else flat.
        returns = df['close'].pct_change().fillna(0)
        strat_returns = np.sign(result_clean) * returns.shift(-1) # Forward returns
        
        # Sharpe
        if strat_returns.std() != 0:
            metrics['sharpe'] = (strat_returns.mean() / strat_returns.std()) * np.sqrt(252 * 24) # Annualized H1 roughly
        else:
            metrics['sharpe'] = 0.0
            
        # 6. Format Response
        # Convert index (timestamps) to list
        timestamps = df.index.to_list() if hasattr(df.index, 'to_list') else list(df.index)
        
        # Safety clean values
        values = []
        for val in result_clean:
             values.append(float(val))
             
        return AlphaResponse(
            signal=values,
            metrics=metrics,
            timestamps=timestamps
        )
            
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Logic Error: {str(e)}")

    finally:
        db.close()
