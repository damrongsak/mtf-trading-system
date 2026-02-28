
import pytest
import pandas as pd
from app.runner.dynamic_bot import DynamicBotExecutor

# Mock Manager
class MockDataManager:
    def get_data(self, symbol):
        # Return dummy OHLCV
        data = {
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [102, 103, 104],
            'volume': [1000, 1200, 1500]
        }
        return pd.DataFrame(data)

@pytest.mark.asyncio
async def test_dynamic_executor_valid():
    code = """
def strategy(data, params):
    return {"direction": "BULLISH", "reason": "Test Signal"}
"""
    executor = DynamicBotExecutor(code, "deploy-123")
    
    state = type("State", (), {"symbol": "XAU/USD", "config_json": {}})()
    manager = MockDataManager()
    
    result = await executor.execute(state, manager)
    assert result["signal"] is not None
    assert result["signal"]["direction"] == "BULLISH"

@pytest.mark.asyncio
async def test_dynamic_executor_error():
    code = """
def strategy(data, params):
    raise ValueError("Crash")
"""
    executor = DynamicBotExecutor(code, "deploy-err")
    
    state = type("State", (), {"symbol": "XAU/USD", "config_json": {}})()
    manager = MockDataManager()
    
    # Should not raise exception, but return None and log error
    result = await executor.execute(state, manager)
    assert result["signal"] is None
    assert "error" in result["logs"]

@pytest.mark.asyncio
async def test_dynamic_executor_no_function():
    code = """
# No strategy function
x = 1
"""
    executor = DynamicBotExecutor(code, "deploy-missing")
    
    state = type("State", (), {"symbol": "XAU/USD", "config_json": {}})()
    manager = MockDataManager()
    
    result = await executor.execute(state, manager)
    assert result["signal"] is None
