import pytest
from unittest.mock import AsyncMock, patch
from app.engine import StrategyEngine, StrategyState
from app.schemas import ExecutionMode
from app.registry import StrategyRegistry

@pytest.mark.asyncio
async def test_process_tuple_return():
    """
    Verify that _process_strategy_logic correctly unpacks a tuple 
    (entries, exits, signal) and calls _execute_signal with the signal dict.
    """
    engine = StrategyEngine()
    
    # Mock strategy state
    strategy_id = "test_tuple_strat"
    config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL, "template_id": "mock_template"}
    state = StrategyState(config)
    
    # Mock the strategy return value: (entries, exits, signal)
    mock_signal = {"direction": "BULLISH", "reason": "Tuple Test"}
    mock_return = (None, None, mock_signal) # entries/exits can be None for this test
    
    # Mock the strategy logic function
    mock_logic_fn = AsyncMock(return_value=mock_return)
    
    # Mock Registry to return our mock function
    with patch.object(StrategyRegistry, 'get_strategy_logic', return_value=mock_logic_fn):
        # Mock _execute_signal to verify it gets called
        with patch.object(engine, '_execute_signal', new_callable=AsyncMock) as mock_exec:
            
            await engine._process_strategy_logic(strategy_id, state)
            
            # ASSERTION: verify _execute_signal was called with the unpacked signal dict
            mock_exec.assert_called_once()
            args, _ = mock_exec.call_args
            # args: (strategy_id, state, signal)
            assert args[0] == strategy_id
            assert args[2] == mock_signal

@pytest.mark.asyncio
async def test_process_dict_return():
    """
    Verify backward compatibility: dict return still works.
    """
    engine = StrategyEngine()
    
    strategy_id = "test_dict_strat"
    config = {"symbol": "EUR_USD", "execution_mode": ExecutionMode.MANUAL, "template_id": "mock_template"}
    state = StrategyState(config)
    
    mock_signal = {"direction": "BEARISH", "reason": "Dict Test"}
    
    mock_logic_fn = AsyncMock(return_value=mock_signal)
    
    with patch.object(StrategyRegistry, 'get_strategy_logic', return_value=mock_logic_fn):
        with patch.object(engine, '_execute_signal', new_callable=AsyncMock) as mock_exec:
            
            await engine._process_strategy_logic(strategy_id, state)
            
            mock_exec.assert_called_once()
            args, _ = mock_exec.call_args
            assert args[2] == mock_signal
