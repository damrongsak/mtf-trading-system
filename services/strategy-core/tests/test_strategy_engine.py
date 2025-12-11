import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.engine import StrategyEngine
from app.schemas import ExecutionMode
import asyncio

@pytest.mark.asyncio
async def test_start_and_stop_strategy():
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
    
    # Mock execution client
    with patch("app.engine.execution_client") as mock_client, \
         patch.object(engine, "_calculate_signal", return_value={"action": "BUY"}) as mock_sig, \
         patch("app.engine.asyncio.sleep", side_effect=asyncio.CancelledError) as mock_sleep:
        
        mock_client.place_order = AsyncMock()
        
        # Run the loop (it will crash/stop when sleep is called)
        try:
            await engine._run_strategy_loop(strategy_id, config)
        except asyncio.CancelledError:
            pass
            
        # Verify signal was calculated
        mock_sig.assert_called_once()
        
        # Verify order was placed
        mock_client.place_order.assert_called_once()
        call_args = mock_client.place_order.call_args[0][0]
        assert call_args["symbol"] == "EUR_USD"
        assert call_args["type"] == "MARKET"

@pytest.mark.asyncio
async def test_execution_logic_manual():
    """
    Verify that MANUAL mode does NOT call execution_client.place_order
    """
    engine = StrategyEngine()
    strategy_id = "manual_strat"
    config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL}
    
    with patch("app.engine.execution_client") as mock_client, \
         patch.object(engine, "_calculate_signal", return_value={"action": "BUY"}) as mock_sig, \
         patch("app.engine.asyncio.sleep", side_effect=asyncio.CancelledError) as mock_sleep:
        
        mock_client.place_order = AsyncMock()
        
        try:
            await engine._run_strategy_loop(strategy_id, config)
        except asyncio.CancelledError:
            pass
            
        mock_client.place_order.assert_not_called()

