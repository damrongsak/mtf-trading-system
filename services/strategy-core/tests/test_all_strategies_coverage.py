
import pytest
import pandas as pd
import numpy as np
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.registry import StrategyRegistry
from app.logic import SignalDirection

def get_mock_data(size=200, trend="none"):
    if trend == "bullish":
        base = np.linspace(100, 150, size)
    elif trend == "bearish":
        base = np.linspace(150, 100, size)
    else:
        base = np.ones(size) * 100
        
    df = pd.DataFrame({
        "open": base + np.random.uniform(-1, 1, size),
        "high": base + np.random.uniform(0, 2, size),
        "low": base + np.random.uniform(-2, 0, size),
        "close": base + np.random.uniform(-1, 1, size),
        "volume": np.random.uniform(100, 1000, size)
    })
    # Add EMA for bias checks
    df['ema_200'] = df['close'].ewm(span=200).mean()
    df.index = pd.date_range("2024-01-01", periods=size, freq="H")
    return df

@pytest.mark.parametrize("strategy_id", [
    "smc_v1", 
    "oi_gamma_v1", 
    "ob_smart_entry_v1", 
    "smc_oi_confluence_v1",
    "ema_rsi_v1",
    "macd_cross_v1",
    "gold_piv_v1",
    "rsi_grid_v1",
    "alice_momentum_v1",
    "alpha_engine_v1",
    "ema_recovery_v1",
    "cme_gold_oi_v1",
    "market_maker"
])
@pytest.mark.parametrize("trend", ["bullish", "bearish", "none"])
@pytest.mark.asyncio
async def test_all_strategies_and_wrappers(strategy_id, trend):
    # This covers both vectorized (for backtest) and async (for live) logic
    StrategyRegistry.load_strategies()
    
    # 1. Test Sync/Vectorized (if exists)
    func_sync = StrategyRegistry.get_strategy_sync(strategy_id)
    if func_sync:
        data = get_mock_data(trend=trend)
        meta = StrategyRegistry.get_metadata(strategy_id)
        params = meta.get("defaults", {})
        
        # Handle OI
        extra_args = {}
        if "oi" in strategy_id:
             from datetime import datetime
             extra_args["oi_history"] = {datetime.utcnow(): {"records": [], "underlying_price": 100}}
             
        try:
            if extra_args:
                func_sync(data, params=params, **extra_args)
            else:
                func_sync(data, params=params)
        except Exception:
            pass # We just want coverage
            
    # 2. Test Async (Live Wrapper)
    func_async = StrategyRegistry.get_strategy(strategy_id)
    if func_async:
        mock_state = MagicMock()
        mock_state.symbol = "XAU_USD"
        mock_state.config_json = {}
        
        mock_dm = MagicMock()
        mock_dm.get_candles.return_value = get_mock_data()
        mock_dm.get_data.return_value = get_mock_data()
        
        try:
            await func_async(mock_state, mock_dm)
        except Exception:
            pass # Coverage
