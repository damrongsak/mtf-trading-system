import pytest
from unittest.mock import MagicMock, patch
from app.fleet import FleetManager
from app.models.strategy import Strategy
from uuid import uuid4
from sqlalchemy import select

@pytest.mark.asyncio
async def test_fleet_manager_loads_active_strategies():
    # Setup
    manager = FleetManager()
    
    # Create fake strategies
    s1 = Strategy(
        id=uuid4(),
        name="Test Strat",
        template_id="SMC_V1",
        fund_id=uuid4(),
        broker_account_id=uuid4(),
        config_json={"symbol": "EUR_USD", "timeframe": "M15"},
        risk_settings={},
        is_active=True
    )
    
    # Mock DB session and its methods
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1]
    mock_db.execute.return_value = mock_result
    
    with patch("app.fleet.SessionLocal", return_value=mock_db), \
         patch("app.fleet.StrategyRegistry.get_strategy", return_value=lambda x: x):
        
        await manager.load_fleet()
        
        # Verify
        assert len(manager.active_strategies) == 1
        assert str(s1.id) in manager.active_strategies
        context = manager.active_strategies[str(s1.id)]
        assert context["symbol"] == "EUR_USD"
        # template_id is not in context but logic function is
        assert context["logic"] is not None

@pytest.mark.asyncio
async def test_fleet_manager_handles_missing_template():
    manager = FleetManager()
    
    s1 = Strategy(
        id=uuid4(),
        name="Broken Strat",
        template_id="NON_EXISTENT",
        fund_id=uuid4(),
        broker_account_id=uuid4(),
        config_json={"symbol": "EUR_USD"},
        risk_settings={},
        is_active=True
    )
    
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1]
    mock_db.execute.return_value = mock_result
    
    with patch("app.fleet.SessionLocal", return_value=mock_db), \
         patch("app.fleet.StrategyRegistry.get_strategy", return_value=None):
        
        await manager.load_fleet()
        
        # Should not be added to active_strategies because template was not found
        assert len(manager.active_strategies) == 0