import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from app.engine import StrategyEngine, StrategyState
from app.schemas import ExecutionMode
from app.market_data import market_data_manager
import asyncio

@pytest.mark.asyncio
async def test_start_and_stop_strategy():
    # Patch RedisSubscriber in CORE module
    with patch("app.engine.core.RedisSubscriber") as MockSubscriber:
        mock_sub = MockSubscriber.return_value
        mock_sub.subscribe = AsyncMock()
        mock_sub.connect = AsyncMock()
        
        engine = StrategyEngine()
        config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL}
        
        # Start
        res = await engine.start_strategy("test_strat", config)
        assert res["status"] == "started"
        assert "test_strat" in engine.active_strategies
        assert mock_sub.subscribe.called
        
        # Stop
        res = await engine.stop_strategy("test_strat")
        assert res["status"] == "stopped"
        assert "test_strat" not in engine.active_strategies

@pytest.mark.asyncio
async def test_execution_logic_auto():
    """
    Verify that AUTO mode calls execution_client.place_order when signal is present.
    """
    with patch("app.engine.core.RedisSubscriber") as MockSubscriber:
        mock_sub = MockSubscriber.return_value
        mock_sub.subscribe = AsyncMock()

        engine = StrategyEngine()
        strategy_id = "auto_strat"
        config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.AUTO}
        
        # Register strategy
        state = StrategyState(config)
        engine.active_strategies[strategy_id] = state
        
        # Set market data with volatility
        dates = pd.date_range("2023-01-01", periods=200, freq="15min")
        df = pd.DataFrame({
            "timestamp": dates,
            "close": [1.1, 1.2]*100, 
            "open": [1.1, 1.2]*100, 
            "high": [1.3, 1.4]*100, 
            "low": [1.0, 1.1]*100,
            "volume": [1000]*200
        })
        market_data_manager.set_data("EUR_USD", df)

        with patch("app.engine.core.execution_client") as mock_client, \
             patch.object(engine, "_process_strategy_logic", new_callable=AsyncMock) as mock_logic, \
             patch("app.engine.core.get_market_sentiment", new_callable=AsyncMock) as mock_sentiment:
            
            mock_sentiment.return_value = {"score": 0.0, "reason": "Neutral"}
            
            # Simulate a tick triggering logic
            tick = {"type": "PRICE", "instrument": "EUR_USD", "bid": "1.12", "ask": "1.12", "time": "2023-01-01T12:00:00Z"}
            
            # on_tick calls FleetManager.tick, which eventually calls _process_strategy_logic
            await engine.on_tick(tick)
             
        with patch("app.engine.core.execution_client") as mock_client:
            mock_client.place_order = AsyncMock()
            # Test _execute_signal directly
            with patch("os.getenv", return_value="true"):
                 await engine._execute_signal(strategy_id, state, {"action": "BUY", "direction": "BULLISH", "stop_loss": 1.0})
                 mock_client.place_order.assert_called()

@pytest.mark.asyncio
async def test_execution_logic_manual():
    """
    Verify that MANUAL mode does NOT call execution_client.place_order
    """
    with patch("app.engine.core.RedisSubscriber") as MockSubscriber:
        engine = StrategyEngine()
        strategy_id = "manual_strat"
        config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL}
        state = StrategyState(config)
        engine.active_strategies[strategy_id] = state
        
        with patch("app.engine.core.execution_client") as mock_client:
            mock_client.place_order = AsyncMock()
            
            # Force execution attempt
            await engine._execute_signal(strategy_id, state, {"action": "BUY", "direction": "BULLISH"})
                
            mock_client.place_order.assert_not_called()