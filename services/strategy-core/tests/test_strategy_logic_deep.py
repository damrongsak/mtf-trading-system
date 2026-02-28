
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from app.strategies.smc_oi_confluence_v1.strategy import strategy as smc_oi_strategy
from app.strategies.oi_gamma_v1.strategy import strategy as oi_gamma_strategy
from app.strategies.oi_gamma_v1.strategy import fetch_latest_oi_snapshot
from app.indicators.trend import calculate_ema, calculate_adx, detect_trend_structure
from app.indicators.volume import calculate_volume_profile

@pytest.mark.asyncio
async def test_smc_oi_confluence_logic_deep():
    df = pd.DataFrame({
        "close": [2000.0]*100,
        "high": [2005.0]*100,
        "low": [1995.0]*100,
        "open": [2000.0]*100,
        "volume": [1000.0]*100
    })
    df.index = pd.date_range("2024-01-01", periods=100, freq="15min")
    
    mock_state = MagicMock()
    mock_state.symbol = "XAUUSD"
    mock_state.config_json = None
    
    mock_dm = MagicMock()
    mock_dm.get_candles.return_value = df
    
    # Mock OI result to trigger branches
    oi_analysis = {
        "records": [
            {'strike': 2010.0, 'call_oi': 1000.0, 'put_oi': 500.0, 'underlying_price': 2000.0},
            {'strike': 1990.0, 'call_oi': 500.0, 'put_oi': 1000.0, 'underlying_price': 2000.0}
        ],
        "snapshot_at": datetime.utcnow(),
        "underlying_futures_price": 2000.0
    }
    
    with patch("app.strategies.smc_oi_confluence_v1.strategy.fetch_latest_oi_snapshot", return_value=oi_analysis), \
         patch("app.strategies.smc_oi_confluence_v1.strategy.analyze_smc") as mock_smc:
        
        mock_smc.return_value = {
            "order_blocks": [{"type": "bullish", "top": 2000, "bottom": 1990}],
            "fvgs": [{"type": "bullish", "top": 2005, "bottom": 2000, "index": 95}],
            "structure": {"trend": "bullish", "pivots": [{"type": "high", "price": 1995, "index": 90}]},
            "liquidity_sweeps": [{"type": "bullish_sweep", "level": 1990, "index": 92, "price": 1988}]
        }
        
        # Test bullish entry logic
        entries, exits, signals, logs = await smc_oi_strategy(mock_state, mock_dm)
        assert entries is not None
