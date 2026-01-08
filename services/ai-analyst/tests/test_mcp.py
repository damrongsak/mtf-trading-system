import pytest
import json
from app.core.mcp import MCPToolAdapter
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_mcp_adapter_create_tool():
    # 1. Define MCP-like Schema
    schema = {
        "type": "object",
        "properties": {
            "price": {"type": "number", "description": "Asset price"},
            "symbol": {"type": "string", "description": "Ticker symbol"}
        }
    }
    
    # 2. Mock Handler
    mock_handler = AsyncMock(return_value="Executed")
    
    # 3. Create Tool
    tool = MCPToolAdapter.create_tool(
        name="trade_executor",
        description="Executes a trade",
        schema=schema,
        execute_fn=mock_handler
    )
    
    # 4. Verify Attributes
    assert tool.name == "trade_executor"
    assert tool.description == "Executes a trade"
    assert "price" in tool.args
    assert "symbol" in tool.args
    
    # 5. Verify Execution
    result = await tool.ainvoke({"price": 100.5, "symbol": "XAUUSD"})
    assert result == "Executed"
    mock_handler.assert_called_with(price=100.5, symbol="XAUUSD")

@pytest.mark.asyncio
async def test_mcp_load_from_json():
    json_def = """
    {
        "name": "get_weather",
        "description": "Get weather info",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            }
        }
    }
    """
    mock_handler = AsyncMock(return_value="Sunny")
    handlers = {"get_weather": mock_handler}
    
    tool = MCPToolAdapter.load_from_json(json_def, handlers)
    
    assert tool.name == "get_weather"
    result = await tool.ainvoke({"city": "New York"})
    assert result == "Sunny"
