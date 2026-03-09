from fastapi import FastAPI, HTTPException, APIRouter, WebSocket, WebSocketDisconnect, Query
print("DEBUG: Starting app/main.py loading...")
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    IndicatorRequest, IndicatorResponse, ATRRequest, BacktestRequest, BacktestResponse,
    RSIRequest, MACDRequest, BBandsRequest, MACDResponse, BBandsResponse,
    SMCRequest, SMCResponse, SMCBatchRequest, SMCBatchResponse, SimulationRequest, SimulationResponse,
    OptimizationResponse, MonteCarloRequest, MonteCarloResponse, StrategyBacktestRequest
)
# from app.indicators import (
#     calculate_ema, calculate_atr, calculate_rsi, calculate_macd, calculate_bbands
# )
# from app.backtest import run_historical_backtest
# from app.indicators.smc import analyze_smc
# from app.utils.helpers import sanitize_numeric_dict
# from app.simulation import run_grid_simulation_logic
# from app.analysis.optimization import run_grid_search
# from app.analysis.monte_carlo import run_monte_carlo
from app.engine import strategy_engine
from app.runner.live import live_runner
from app.workers.reconciliation import reconciliation_worker
# from app.adapters.oanda_history import OandaHistoryAdapter
import pandas as pd
import numpy as np
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import traceback
import logging
import time

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

# Original v1 health check removed to avoid duplicate routes


@router.get("/market/candles")
def get_candles(
    symbol: str, 
    timeframe: str, 
    from_time: Optional[datetime] = None, 
    to_time: Optional[datetime] = None, 
    count: int = 500,
    data_source: str = "CTRADER"
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
        from app.indicators import calculate_ema
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
        from app.indicators import calculate_atr
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
        from app.indicators import calculate_rsi
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
        from app.indicators import calculate_macd
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
            macd=clean_series(macd_res['macd']),
            signal=clean_series(macd_res['signal']),
            hist=clean_series(macd_res['hist'])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/bbands", response_model=BBandsResponse)
def get_bbands(req: BBandsRequest):
    try:
        from app.indicators import calculate_bbands
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
             
        # Columns are already normalized to lower case in calculate_adx
        # adx, dmp, dmn
        
        def clean(s):
            # Ensure safe numeric type
            s = pd.to_numeric(s, errors='coerce')
            values = []
            for val in s:
                 if pd.isna(val) or np.isinf(val):
                     values.append(None)
                 else:
                     values.append(float(val))
            return values

        return ADXResponse(
            adx=clean(adx_df['adx']) if 'adx' in adx_df else [],
            dmp=clean(adx_df['dmp']) if 'dmp' in adx_df else [],
            dmn=clean(adx_df['dmn']) if 'dmn' in adx_df else []
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/market-state")
def get_market_state(req: SMCRequest):
    try:
        from app.analysis.market_state import MarketStateService
        import json
        df = _prepare_df(req)
        
        second_df = None
        if req.second_close:
            second_df = pd.DataFrame({"close": req.second_close})
        
        # Prepare OI data if provided
        oi_data = None
        if req.oi_call and req.oi_put and req.oi_strikes:
            oi_data = {
                "call_oi": req.oi_call,
                "put_oi": req.oi_put,
                "strikes": req.oi_strikes,
                "current_price": float(df['close'].iloc[-1])
            }
            
        result = MarketStateService.analyze_state(df, second_df, oi_data)
        
        # Use pandas to-json for robust nan handling (converts nan to null)
        json_str = pd.Series(result).to_json()
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Market state calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _prepare_df(req: SMCRequest) -> pd.DataFrame:
    data = {
        "open": req.open,
        "high": req.high,
        "low": req.low,
        "close": req.close
    }
    if req.volume:
        data["volume"] = req.volume
        
    df = pd.DataFrame(data)
    if req.timestamps and len(req.timestamps) == len(df):
        df.index = pd.to_datetime(req.timestamps, format='ISO8601')
        
    if len(df) < 3:
         raise HTTPException(status_code=400, detail="Not enough data points")
    return df

@router.post("/calculate/smc", response_model=SMCResponse)
def get_smc(req: SMCRequest):
    try:
        from app.indicators.smc import analyze_smc
        from app.utils.helpers import sanitize_numeric_dict
        df = _prepare_df(req)
        result = analyze_smc(df, req.symbol, req.timeframe)
        sanitized_result = sanitize_numeric_dict(result)
        return SMCResponse(**sanitized_result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SMC calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate/smc/batch", response_model=SMCBatchResponse)
def get_smc_batch(req: SMCBatchRequest):
    try:
        from app.indicators.smc import analyze_smc
        results = {}
        for symbol, smc_req in req.requests.items():
            try:
                df = _prepare_df(smc_req)
                result = analyze_smc(df, smc_req.symbol, smc_req.timeframe)
                results[symbol] = SMCResponse(**result)
            except Exception as e:
                logger.error(f"Error processing {symbol} in batch: {e}")
                results[symbol] = SMCResponse(order_blocks=[], fvgs=[], liquidity_sweeps=[])
        
        return SMCBatchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    try:
        from app.simulation import run_grid_simulation_logic
        return run_grid_simulation_logic(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest", response_model=BacktestResponse)
def run_backtest_endpoint(req: BacktestRequest):
    try:
        from app.backtest import run_historical_backtest
        return run_historical_backtest(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest/custom", response_model=BacktestResponse)
def run_custom_backtest_endpoint(req: StrategyBacktestRequest):
    try:
        from app.backtest import run_custom_backtest
        return run_custom_backtest(req)
    except Exception as e:
        logger.error(f"Custom backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.websocket("/ws/prices")
# async def websocket_endpoint(websocket: WebSocket, symbols: str = Query("EUR_USD,XAU_USD")):
#     await websocket.close(code=1000, reason="Use API Gateway /api/v1/stream/prices")

@router.post("/strategies/{strategy_id}/start")
async def start_strategy_endpoint(strategy_id: str, config: dict):
    # Ensure LiveRunner is active
    from app.runner.live import live_runner
    from app.engine import strategy_engine
    await live_runner.start()
    return await strategy_engine.start_strategy(strategy_id, config)

@router.post("/strategies/{strategy_id}/stop")
async def stop_strategy_endpoint(strategy_id: str):
    from app.engine import strategy_engine
    return await strategy_engine.stop_strategy(strategy_id)

@router.post("/backtest/optimize", response_model=OptimizationResponse)
def run_optimization_endpoint(req: StrategyBacktestRequest):
    try:
        # Check optimization config (it's a dict in StrategyBacktestRequest per backend spec?)
        # Actually strategy-core schemas need to be checked.
        # But assuming we pass 'optimization' in the body
        if not req.optimization or not req.optimization.param_grid:
             raise HTTPException(status_code=400, detail="Optimization config required")
             
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
        # Run Grid Search
        results = run_grid_search(
            data=df,
            param_grid=req.optimization.param_grid,
            capital=req.initial_capital,
            fees=req.fees,
            code=req.code # Pass custom code
        )
        
        response = OptimizationResponse(results=results)
        
        if req.strategy_id:
            from app.utils.persistence import save_strategy_result
            # Results are already dicts (from run_grid_search)
            save_strategy_result(req.strategy_id, 'optimization', results)
            
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest/monte-carlo", response_model=MonteCarloResponse)
def run_monte_carlo_endpoint(req: MonteCarloRequest):
    try:
        logger.info(f"Received monte carlo request for {len(req.trades)} trades")
        from app.analysis.monte_carlo import run_monte_carlo  # Import here to ensure latest version is used? No, should be top level but fine.
        metrics = run_monte_carlo(req.trades, n_sims=req.iterations)
        
        logger.info(f"Monte Carlo returned metrics: {metrics.keys()}")
        # logger.info(f"Metrics content: {metrics}") # Verbose but useful
        
        if not metrics:
             raise HTTPException(status_code=400, detail="No valid trades for simulation")
             
        if req.strategy_id:
            from app.utils.persistence import save_strategy_result
            save_strategy_result(req.strategy_id, 'simulation', metrics)

        return metrics
             
        return MonteCarloResponse(
            iterations=metrics["iterations"],
            max_drawdown=metrics["max_drawdown"],
            total_return=metrics["total_return"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/drift")
def analyze_system_drift(window_hours: int = 24):
    try:
        from app.analysis.monitor import performance_monitor
        return performance_monitor.analyze_drift(window_hours=window_hours)
    except Exception as e:
        logger.error(f"Drift endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Live Deployment Endpoints ---

@router.post("/live/deploy")
async def deploy_strategy_instance(payload: dict):
    from app.fleet import FleetManager
    # payload contains deployment_id
    deployment_id = payload.get("deployment_id")
    if not deployment_id:
        raise HTTPException(status_code=400, detail="Missing deployment_id")
    
    # Reload fleet to pick up new deployment
    FleetManager.get_instance().add_deployment(deployment_id)
    
    # Ensure LiveRunner is running
    if not live_runner._running:
        await live_runner.start()
        
    return {"status": "deployed", "id": deployment_id}

@router.post("/live/stop/{deployment_id}")
async def stop_strategy_instance(deployment_id: str):
    from app.fleet import FleetManager
    FleetManager.get_instance().remove_deployment(deployment_id)
    return {"status": "stopped", "id": deployment_id}

app.include_router(router)
from app.foundry.router import router as foundry_router
from app.routers.quant import router as quant_router
app.include_router(foundry_router, prefix="/api/v1")
app.include_router(quant_router, prefix="/api/v1/quant", tags=["Quant Layer"])
from app.engine.router import router as alpha_router
app.include_router(alpha_router, prefix="/api/v1")
from app.routers.plugins import router as plugins_internal_router
app.include_router(plugins_internal_router)

from app.routers.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

from app.routers.strategies import router as strategies_router
app.include_router(strategies_router, prefix="/api/v1")

from app.routers.execution_flow import router as execution_flow_router
app.include_router(execution_flow_router, prefix="/api/v1")

from app.routers.market import router as market_router
app.include_router(market_router, prefix="/api/v1")

from app.routers.gamma import router as gamma_router
app.include_router(gamma_router, prefix="/api/v1")

from app.routers.risk import router as risk_router
app.include_router(risk_router, prefix="/api/v1")

# Global Workers
from app.workers.reconciliation import reconciliation_worker
from app.workers.market_context_worker import context_worker

@app.on_event("startup")
async def startup_event():
    # Only start workers in main container, ignore in tests/alembic unless specified
    import os
    if os.getenv("RUN_WORKERS", "true").lower() == "true":
        await context_worker.start()
        logger.info("Market Context Worker started.")
        
        # Load Strategy Fleet from Database
        from app.fleet import FleetManager
        await FleetManager.get_instance().load_fleet()
        logger.info("Strategy Fleet Loaded on startup.")



@app.on_event("shutdown")
async def shutdown_event():
    from app.runner.live import live_runner
    await live_runner.stop()
    
    from app.workers.reconciliation import reconciliation_worker
    await reconciliation_worker.stop()
    
    # TODO: Disable Indicator Worker for now
    # global indicator_worker
    # if indicator_worker:
    #     await indicator_worker.stop()
    
    import os
    if os.getenv("RUN_WORKERS", "true").lower() == "true":
        await context_worker.stop()
        logger.info("Market Context Worker stopped.")
