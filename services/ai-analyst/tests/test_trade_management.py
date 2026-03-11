import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.trade_manager import TradeManagementAgent
from app.core.workflow import registry

@pytest.fixture
def mock_gemini():
    client = MagicMock()
    client.generate_content = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_trade_management_logic(mock_gemini):
    # 1. Setup Mock Response from Gemini
    mock_gemini.generate_content.return_value = {
        "text": json.dumps({
            "decisions": [
                {
                    "broker_trade_id": "pos_123",
                    "broker_account_id": "acc_abc",
                    "action": "MOVE_TO_BE",
                    "sl_price": 2650.5,
                    "tp_price": 2750.0,
                    "reason": "Trade in 1:1 profit"
                }
            ]
        })
    }

    # 2. Mock the modify_trade tool in registry
    mock_tool = AsyncMock()
    mock_tool.run_tool.return_value = "✅ Success"
    
    with patch.dict(registry._tools, {"modify_trade": mock_tool}):
        agent = TradeManagementAgent(mock_gemini)
        
        trades = [
            {
                "id": "pos_123",
                "broker_account_id": "acc_abc",
                "symbol": "XAUUSD",
                "direction": "LONG",
                "entry_price": 2650.0,
                "current_price": 2665.0,
                "sl": 2640.0,
                "tp": 2750.0,
                "pnl_usd": 150.0
            }
        ]
        
        results = await agent.manage_trades(trades, "Bullish momentum on H1, price reached 1:1 RR")
        
        # 3. Assertions
        assert len(results) == 1
        assert results[0]["result"] == "✅ Success"
        assert results[0]["action"] == "MOVE_TO_BE"
        
        # Verify tool was called with correct params
        mock_tool.run_tool.assert_called_once()
        args, kwargs = mock_tool.run_tool.call_args
        tool_input = args[0]
        assert tool_input["broker_trade_id"] == "pos_123"
        assert tool_input["sl_price"] == 2650.5
