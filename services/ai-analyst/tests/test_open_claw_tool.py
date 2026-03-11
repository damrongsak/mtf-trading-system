import pytest
from unittest.mock import AsyncMock, patch
from app.tools.open_claw import OpenClawResearcherTool, OpenClawInput

@pytest.mark.asyncio
async def test_open_claw_tool_success():
    """Verify tool successfully calls external API and returns result."""
    tool = OpenClawResearcherTool()
    
    # Mock Response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": "Gold is bullish due to Fed pivot rumors."})
    
    with patch("aiohttp.ClientSession.post", return_value=mock_response):
        input_data = OpenClawInput(task="Analyze Gold sentiment")
        result = await tool.run_tool(input_data)
        
        assert "Gold is bullish" in result
        assert "OpenClaw Research Result" in result

@pytest.mark.asyncio
async def test_open_claw_tool_error():
    """Verify tool handles API errors gracefully."""
    tool = OpenClawResearcherTool()
    
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    
    with patch("aiohttp.ClientSession.post", return_value=mock_response):
        input_data = OpenClawInput(task="Error task")
        result = await tool.run_tool(input_data)
        
        assert "Error from OpenClaw service" in result
        assert "500" in result
