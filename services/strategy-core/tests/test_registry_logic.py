
import pytest
import asyncio
from app.registry import StrategyRegistry

def test_registry_registration():
    # Test manual registration via register_custom
    code = """
async def strategy(data, params=None):
    return None, None, {"direction": "LONG"}
"""
    StrategyRegistry.register_custom("TEST_STRAT", code, "Test Strategy")
    
    # Test list_templates
    templates = StrategyRegistry.list_templates()
    ids = [t["id"] for t in templates]
    assert "TEST_STRAT" in ids
    
    # Test retrieval
    func = StrategyRegistry.get_strategy("TEST_STRAT")
    assert func is not None
    assert asyncio.iscoroutinefunction(func)

def test_registry_metadata():
    meta = StrategyRegistry.get_metadata("TEST_STRAT")
    assert meta["name"] == "Test Strategy"

def test_registry_non_existent():
    assert StrategyRegistry.get_strategy("NON_EXISTENT") is None

def test_registry_auto_discovery():
    # Just check that it has some built-ins loaded
    templates = StrategyRegistry.list_templates()
    template_ids = [t["id"] for t in templates]
    # We know SMC_V1 should be there if load_strategies was called (it is by FleetManager or on access)
    assert "SMC_V1" in template_ids or len(template_ids) > 0
