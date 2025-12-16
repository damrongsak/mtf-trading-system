import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from app.engine import StrategyEngine, StrategyState
from app.schemas import ExecutionMode
import asyncio

@pytest.mark.asyncio
async def test_start_and_stop_strategy():
    with patch("app.engine.OandaHistoryAdapter") as MockAdapter:
        # Configure mock to return a dummy dataframe
        mock_instance = MockAdapter.return_value
        # Mock fetch_candles_range to return a valid DataFrame
        mock_instance.fetch_candles_range.return_value = pd.DataFrame({
            "open": [1.0]*500, "high": [1.2]*500, "low": [0.9]*500, "close": [1.1]*500
        })
        
        engine = StrategyEngine()
        config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL}
        
        # Start
        res = await engine.start_strategy("test_strat", config)
        assert res["status"] == "started"
        assert "test_strat" in engine.active_strategies
        
        # Stop
        res = await engine.stop_strategy("test_strat")
        assert res["status"] == "stopped"
        assert "test_strat" not in engine.active_strategies

@pytest.mark.asyncio
async def test_execution_logic_auto():
    """
    Verify that AUTO mode calls execution_client.place_order when signal is present.
    """
    engine = StrategyEngine()
    strategy_id = "auto_strat"
    config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.AUTO}
    
    # Mock active strategy state
    engine.active_strategies[strategy_id] = StrategyState(config)
    # Ensure data is present
    engine.active_strategies[strategy_id].data["M15"] = pd.DataFrame(
        {"close": [1.1]*200, "open": [1.1]*200, "high": [1.1]*200, "low": [1.1]*200}
    )

    with patch("app.engine.execution_client") as mock_client, \
         patch.object(engine, "_calculate_signal", new_callable=AsyncMock) as mock_sig:
             
        mock_sig.return_value = {"action": "BUY", "direction": "BULLISH"}
        
        mock_client.place_order = AsyncMock()
        
        # Simulate a tick triggering logic
        tick = {"instrument": "EUR_USD", "bid": 1.12, "ask": 1.12, "time": "2023-01-01T12:00:00Z"}
        
        # We need to ensure _process_tick is called. active_strategies key and symbol must match.
        await engine.on_tick(tick)
            
        # Verify signal was calculated
        mock_sig.assert_called()
        
        # Verify order was placed (live trading check logic inside _execute_signal might block it if env var not set to true)
        # In test env, LIVE_TRADING_ENABLED might be false.
        # We should patch os.getenv to allow it
        with patch("os.getenv", return_value="true"):
             await engine._execute_signal(strategy_id, engine.active_strategies[strategy_id], {"direction": "BULLISH"})
             mock_client.place_order.assert_called()

@pytest.mark.asyncio
async def test_execution_logic_manual():
    """
    Verify that MANUAL mode does NOT call execution_client.place_order
    """
    engine = StrategyEngine()
    strategy_id = "manual_strat"
    config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL}
    engine.active_strategies[strategy_id] = StrategyState(config)
    
    with patch("app.engine.execution_client") as mock_client:
        mock_client.place_order = AsyncMock()
        
        # Force execution attempt
        await engine._execute_signal(strategy_id, engine.active_strategies[strategy_id], {"direction": "BULLISH"})
            
        mock_client.place_order.assert_not_called()

