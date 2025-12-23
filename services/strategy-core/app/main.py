from fastapi import FastAPI, HTTPException, APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    IndicatorRequest, IndicatorResponse, ATRRequest, BacktestRequest, BacktestResponse,
    RSIRequest, MACDRequest, BBandsRequest, MACDResponse, BBandsResponse,
    SMCRequest, SMCResponse, SMCBatchRequest, SMCBatchResponse, SimulationRequest, SimulationResponse,
    OptimizationResponse, MonteCarloRequest, MonteCarloResponse
)
from app.indicators import (
    calculate_ema, calculate_atr, calculate_rsi, calculate_macd, calculate_bbands
)
from app.backtest import run_historical_backtest
from app.smc import detect_order_blocks, detect_fvg, detect_liquidity_sweeps
from app.simulation import run_grid_simulation_logic
from app.analysis.optimization import run_grid_search
from app.analysis.monte_carlo import run_monte_carlo
from app.analysis.monte_carlo import run_monte_carlo
from app.engine import strategy_engine
from app.runner.live import live_runner
# from app.adapters.oanda_history import OandaHistoryAdapter
import pandas as pd
import numpy as np
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Strategy Core Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router definition ---
router = APIRouter(prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "strategy-core"}

@router.get("/health")
def health_check_v1():
    return {"status": "ok", "service": "strategy-core"}

@router.get("/market/candles")
def get_candles(
    symbol: str, 
    timeframe: str, 
    from_time: Optional[datetime] = None, 
    to_time: Optional[datetime] = None, 
    count: int = 500,
    data_source: str = "OANDA"
):
    try:
        from app.backtest import fetch_data_from_db
        from app.models.market import MarketSymbol
        from app.models.data_source import DataSource
        from app.database import SessionLocal
        
        db = SessionLocal()
        
        # OANDA v20 expects underscores instead of slashes, but DB stores as is or specific convention.
        # Assuming DB stores "XAU_USD" or "EUR_USD".
        # We need to map the requested symbol string to a MarketSymbol ID.
        # We also need to filter by Data Source if provided (or default).
        
        # Flexible symbol matching (try as-is, then replace)
        target_symbol = symbol
        
        query = db.query(MarketSymbol).join(DataSource).filter(
            (MarketSymbol.symbol == target_symbol) | (MarketSymbol.symbol == target_symbol.replace("/", "_")),
            DataSource.name == data_source
        )
        ms = query.first()
        
        if not ms:
            db.close()
            # Fallback or error? For now empty.
            return {"data": []}
            
        market_symbol_id = ms.id
        db.close()
        
        # Determine time range for DB fetch
        end_dt = to_time if to_time else datetime.utcnow()
        # Default to wider range if start not provided, will slice later
        start_dt = from_time if from_time else (end_dt - pd.Timedelta(days=60)) 
        
        df = fetch_data_from_db(
            market_symbol_id=market_symbol_id, 
            timeframe=timeframe, 
            start_date=start_dt, 
            end_date=end_dt
        )
        if df.empty:
            return {"data": []}
            
        # Slice to last 'count' rows if needed
        if count and len(df) > count:
            df = df.iloc[-count:]
            
        # Reset index to make timestamp a column, convert to ISO string
        df = df.reset_index()
        # Handle nan/inf
        df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
        
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/ema", response_model=IndicatorResponse)
def get_ema(req: IndicatorRequest):
    try:
        data = pd.Series(req.data)
        span = req.params.get("span", 14)
        ema = calculate_ema(data, span=span)
        # Replace NaN and Inf with None for JSON serialization
        # Custom safe cleaning
        values = []
        for val in ema:
            if pd.isna(val) or np.isinf(val):
                values.append(None)
            else:
                values.append(float(val))
        return IndicatorResponse(values=values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/atr", response_model=IndicatorResponse)
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

@router.post("/calculate/rsi", response_model=IndicatorResponse)
def get_rsi(req: RSIRequest):
    try:
        close = pd.Series(req.close)
        rsi = calculate_rsi(close, window=req.window)
        values = []
        for val in rsi:
            if pd.isna(val) or np.isinf(val):
                values.append(None)
            else:
                values.append(float(val))
        return IndicatorResponse(values=values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/macd", response_model=MACDResponse)
def get_macd(req: MACDRequest):
    try:
        close = pd.Series(req.close)
        macd_res = calculate_macd(close, fast=req.fast, slow=req.slow, signal=req.signal)
        
        def clean_series(s):
            values = []
            for val in s:
                if pd.isna(val) or np.isinf(val):
                    values.append(None)
                else:
                    values.append(float(val))
            return values
            
        return MACDResponse(
            macd=clean_series(macd_res.macd),
            signal=clean_series(macd_res.signal),
            hist=clean_series(macd_res.hist)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/bbands", response_model=BBandsResponse)
def get_bbands(req: BBandsRequest):
    try:
        close = pd.Series(req.close)
        bb = calculate_bbands(close, window=req.window, alpha=req.alpha)
        
        def clean_series(s):
            values = []
            for val in s:
                if pd.isna(val) or np.isinf(val):
                    values.append(None)
                else:
                    values.append(float(val))
            return values
            
        return BBandsResponse(
            upper=clean_series(bb.upper),
            middle=clean_series(bb.middle),
            lower=clean_series(bb.lower)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ADXRequest(BaseModel):
    high: List[float]
    low: List[float]
    close: List[float]
    length: int = 14

class ADXResponse(BaseModel):
    adx: List[Optional[float]]
    dmp: List[Optional[float]]
    dmn: List[Optional[float]]

@router.post("/calculate/adx", response_model=ADXResponse)
def get_adx(req: ADXRequest):
    try:
        from app.indicators import calculate_adx
        high = pd.Series(req.high)
        low = pd.Series(req.low)
        close = pd.Series(req.close)
        
        adx_df = calculate_adx(high, low, close, length=req.length)
        
        if adx_df is None or adx_df.empty:
             return ADXResponse(adx=[], dmp=[], dmn=[])
             
        # Columns are dynamic like ADX_14, DMP_14. We grab by index or flexible naming.
        # pandas-ta output order: ADX, DMP, DMN usually.
        # But safest is to find cols starting with ADX, DMP, DMN
        cols = adx_df.columns
        adx_col = next((c for c in cols if c.startswith('ADX')), None)
        dmp_col = next((c for c in cols if c.startswith('DMP')), None)
        dmn_col = next((c for c in cols if c.startswith('DMN')), None)
        
        def clean(s):
            values = []
            for val in s:
                 if pd.isna(val) or np.isinf(val):
                     values.append(None)
                 else:
                     values.append(float(val))
            return values

        return ADXResponse(
            adx=clean(adx_df[adx_col]) if adx_col else [],
            dmp=clean(adx_df[dmp_col]) if dmp_col else [],
            dmn=clean(adx_df[dmn_col]) if dmn_col else []
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/smc", response_model=SMCResponse)
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

@router.post("/calculate/smc/batch", response_model=SMCBatchResponse)
def get_smc_batch(req: SMCBatchRequest):
    try:
        results = {}
        for symbol, smc_req in req.requests.items():
            try:
                data = {
                    "open": smc_req.open,
                    "high": smc_req.high,
                    "low": smc_req.low,
                    "close": smc_req.close
                }
                if smc_req.volume:
                    data["volume"] = smc_req.volume
                    
                df = pd.DataFrame(data)
                
                if len(df) < 3:
                     # Skip or return empty
                     results[symbol] = SMCResponse(order_blocks=[], fvgs=[], liquidity_sweeps=[])
                     continue
    
                obs = detect_order_blocks(df)
                fvgs = detect_fvg(df)
                sweeps = detect_liquidity_sweeps(df)
                
                results[symbol] = SMCResponse(order_blocks=obs, fvgs=fvgs, liquidity_sweeps=sweeps)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                # Return empty/safe response on individual failure so entire batch doesn't fail
                results[symbol] = SMCResponse(order_blocks=[], fvgs=[], liquidity_sweeps=[])
        
        return SMCBatchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    try:
        return run_grid_simulation_logic(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest", response_model=BacktestResponse)
def run_backtest_endpoint(req: BacktestRequest):
    try:
        return run_historical_backtest(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.websocket("/ws/prices")
# async def websocket_endpoint(websocket: WebSocket, symbols: str = Query("EUR_USD,XAU_USD")):
#     await websocket.close(code=1000, reason="Use API Gateway /api/v1/stream/prices")

@router.post("/strategies/{strategy_id}/start")
async def start_strategy_endpoint(strategy_id: str, config: dict):
    # Ensure LiveRunner is active
    await live_runner.start()
    return await strategy_engine.start_strategy(strategy_id, config)

@router.post("/strategies/{strategy_id}/stop")
async def stop_strategy_endpoint(strategy_id: str):
    return await strategy_engine.stop_strategy(strategy_id)

@router.post("/backtest/optimize", response_model=OptimizationResponse)
def run_optimization_endpoint(req: BacktestRequest):
    try:
        if not req.optimization or not req.optimization.param_grid:
             raise HTTPException(status_code=400, detail="Optimization config required")
             
        # Fetch Data from DB
        # Fetch Data from DB
        from app.backtest import fetch_data_from_db
        from app.utils.helpers import resolve_market_symbol_id
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            ms_id = resolve_market_symbol_id(db, req.symbol)
            if not ms_id:
                # Fallback to OANDA default or error
                raise ValueError(f"MarketSymbol not found for {req.symbol}")
        finally:
            db.close()

        df = fetch_data_from_db(
             market_symbol_id=ms_id,
             timeframe=req.timeframe,
             start_date=req.start_date,
             end_date=req.end_date
        )
        
        if df.empty:
            return OptimizationResponse(results=[])
            
        # Run Grid Search
        results = run_grid_search(
            data=df,
            param_grid=req.optimization.param_grid,
            capital=req.initial_capital,
            fees=req.fees
        )
        
        return OptimizationResponse(results=results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest/monte-carlo", response_model=MonteCarloResponse)
def run_monte_carlo_endpoint(req: MonteCarloRequest):
    try:
        metrics = run_monte_carlo(req.trades, n_sims=req.iterations)
        if not metrics:
             raise HTTPException(status_code=400, detail="No valid trades for simulation")
             
        return MonteCarloResponse(
            iterations=metrics["iterations"],
            max_drawdown=metrics["max_drawdown"],
            total_return=metrics["total_return"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Strategy Engine (Primary Event Consumer)...")
    await strategy_engine.start()

@app.on_event("shutdown")
async def shutdown_event():
    await live_runner.stop()
