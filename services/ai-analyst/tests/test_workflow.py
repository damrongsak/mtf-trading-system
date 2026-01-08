import pytest
from app.core.workflow import ToolRegistry, registry

@pytest.fixture
def clean_registry():
    # Setup
    old_tools = registry._tools.copy()
    registry._tools.clear()
    yield registry
    # Teardown
    registry._tools = old_tools

@pytest.mark.asyncio
async def test_registry_register_and_get(clean_registry):
    async def mock_tool(x):
        return x * 2

    clean_registry.register("mock_tool", mock_tool)
    
    # Test get
    retrieved = clean_registry.get("mock_tool")
    assert retrieved == mock_tool
    
    # Test execute
    result = await clean_registry.execute("mock_tool", x=5)
    assert result == 10

@pytest.mark.asyncio
async def test_registry_missing_tool(clean_registry):
    with pytest.raises(ValueError, match="Tool unknown not found"):
        await clean_registry.execute("unknown")
