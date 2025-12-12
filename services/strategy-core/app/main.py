from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import IndicatorRequest, IndicatorResponse, ATRRequest, BacktestRequest, BacktestResponse
from app.indicators import calculate_ema, calculate_atr
from app.backtest import run_historical_backtest
import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from app.adapters.oanda_history import OandaHistoryAdapter

app = FastAPI(title="Strategy Core Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "strategy-core"}

@app.get("/market/candles")
def get_candles(
    symbol: str, 
    timeframe: str, 
    from_time: Optional[datetime] = None, 
    to_time: Optional[datetime] = None, 
    count: int = 500
):
    try:
        adapter = OandaHistoryAdapter()
        df = adapter.fetch_candles_range(
            symbol=symbol, 
            timeframe=timeframe, 
            from_time=from_time, 
            to_time=to_time, 
            count=count
        )
        
        if df.empty:
            return {"data": []}
            
        # Reset index to make timestamp a column, convert to ISO string
        df = df.reset_index()
        # Handle nan/inf
        df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
        
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

from app.schemas import RSIRequest, MACDRequest, BBandsRequest, MACDResponse, BBandsResponse
from app.indicators import calculate_rsi, calculate_macd, calculate_bbands

@app.post("/calculate/rsi", response_model=IndicatorResponse)
def get_rsi(req: RSIRequest):
    try:
        close = pd.Series(req.close)
        rsi = calculate_rsi(close, window=req.window)
        # Handle NaN/Inf
        values = rsi.replace([np.inf, -np.inf], np.nan).where(pd.notnull(rsi), None).tolist()
        return IndicatorResponse(values=values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate/macd", response_model=MACDResponse)
def get_macd(req: MACDRequest):
    try:
        close = pd.Series(req.close)
        macd_res = calculate_macd(close, fast=req.fast, slow=req.slow, signal=req.signal)
        
        def clean_series(s):
            return s.replace([np.inf, -np.inf], np.nan).where(pd.notnull(s), None).tolist()
            
        return MACDResponse(
            macd=clean_series(macd_res.macd),
            signal=clean_series(macd_res.signal),
            hist=clean_series(macd_res.hist)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate/bbands", response_model=BBandsResponse)
def get_bbands(req: BBandsRequest):
    try:
        close = pd.Series(req.close)
        bb = calculate_bbands(close, window=req.window, alpha=req.alpha)
        
        def clean_series(s):
            return s.replace([np.inf, -np.inf], np.nan).where(pd.notnull(s), None).tolist()
            
        return BBandsResponse(
            upper=clean_series(bb.upper),
            middle=clean_series(bb.middle),
            lower=clean_series(bb.lower)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.schemas import SMCRequest, SMCResponse
from app.smc import detect_order_blocks, detect_fvg, detect_liquidity_sweeps

@app.post("/calculate/smc", response_model=SMCResponse)
def get_smc(req: SMCRequest):
    try:
        data = {
            "open": req.open,
            "high": req.high,
            "low": req.low,
            "close": req.close
        }
        if req.volume:
            data["volume"] = req.volume
            
        df = pd.DataFrame(data)
        
        if len(df) < 3:
             raise HTTPException(status_code=400, detail="Not enough data points")

        obs = detect_order_blocks(df)
        fvgs = detect_fvg(df)
        sweeps = detect_liquidity_sweeps(df)
        
        return SMCResponse(order_blocks=obs, fvgs=fvgs, liquidity_sweeps=sweeps)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.schemas import SimulationRequest, SimulationResponse
from app.simulation import run_grid_simulation_logic

@app.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    try:
        return run_grid_simulation_logic(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backtest", response_model=BacktestResponse)
def run_backtest_endpoint(req: BacktestRequest):
    try:
        return run_historical_backtest(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import WebSocket, WebSocketDisconnect, Query
from app.streaming import price_streamer

@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket, symbols: str = Query("EUR_USD,XAU_USD")):
    await websocket.accept()
    try:
        # Parse comma-separated string to list
        instruments = [s.strip() for s in symbols.split(",") if s.strip()]
        async for data in price_streamer.stream(instruments):
            await websocket.send_json(data)
    except WebSocketDisconnect:
        print("Client disconnected from price stream")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
