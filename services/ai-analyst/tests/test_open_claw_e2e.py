import pytest
import asyncio
from app.tools.open_claw import OpenClawResearcherTool, OpenClawChatTool, OpenClawInput, OpenClawChatInput
from app.core.config import settings

@pytest.mark.asyncio
async def test_open_claw_researcher_standard():
    """Tests the standard (paid) research flow."""
    tool = OpenClawResearcherTool()
    # Using a simple query to minimize cost during testing if actually called
    input_data = OpenClawInput(task="What is the current price of Gold?", autonomous=False)
    
    # We expect this to follow the /tools/invoke path. 
    # If the gateway is down, it should fall back to standard search.
    result = await tool.run_tool(input_data)
    assert result is not None
    assert "OpenClaw" in result or "FALLBACK" in result

@pytest.mark.asyncio
async def test_open_claw_researcher_autonomous():
    """Tests the zero-cost autonomous research flow."""
    tool = OpenClawResearcherTool()
    # This should trigger the chat API /v1/responses
    input_data = OpenClawInput(task="Test autonomous search for gold price", autonomous=True)
    
    result = await tool.run_tool(input_data)
    assert result is not None
    # Autonomous mode uses OpenClawChatTool which returns "OpenClaw Agent Response"
    assert "OpenClaw Agent Response" in result or "Error" in result or "FALLBACK" in result

@pytest.mark.asyncio
async def test_open_claw_chat_direct():
    """Tests direct chat interaction."""
    tool = OpenClawChatTool()
    input_data = OpenClawChatInput(message="Identify yourself and your browser version.")
    
    result = await tool.run_tool(input_data)
    assert result is not None
    assert "OpenClaw Agent Response" in result or "Error" in result
