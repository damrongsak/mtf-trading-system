import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.fleet import FleetLoader
from app.models.strategy import StrategyModel
from uuid import uuid4

@pytest.mark.asyncio
async def test_fleet_loader_loads_active_strategies():
    # Setup Mocks
    mock_engine = MagicMock()
    mock_engine.start_strategy = AsyncMock(return_value={"status": "started"})
    
    mock_db_session = MagicMock()
    
    # Create fake strategies
    s1 = StrategyModel(
        id=uuid4(),
        template_id="SMC_V1",
        broker_account_id=uuid4(),
        config_json={"symbol": "EUR_USD", "timeframe": "M15"},
        is_active=True
    )
    # s2 is inactive, should be skipped
    s2 = StrategyModel(
        id=uuid4(),
        template_id="MACD_V1",
        broker_account_id=uuid4(),
        config_json={"symbol": "GBP_USD"},
        is_active=False 
    )
    
    # Mock DB query
    # We mock the context manager 'get_db_context'
    with patch("app.fleet.get_db_context") as mock_get_context:
        mock_get_context.return_value.__enter__.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.all.return_value = [s1] # returning only active since filter returns active
        
        loader = FleetLoader(mock_engine)
        await loader.load_fleet()
        
        # Verify
        assert mock_engine.start_strategy.call_count == 1
        args, kwargs = mock_engine.start_strategy.call_args
        
        assert args[0] == str(s1.id)
        assert args[1]["template_id"] == "SMC_V1"
        assert args[1]["symbol"] == "EUR_USD"

@pytest.mark.asyncio
async def test_fleet_loader_handles_missing_config():
    mock_engine = MagicMock()
    mock_engine.start_strategy = AsyncMock()
    mock_db_session = MagicMock()
    
    # Missing symbol in config
    s1 = StrategyModel(
        id=uuid4(),
        template_id="BROKEN",
        broker_account_id=uuid4(),
        config_json={"foo": "bar"}, # Missing symbol
        is_active=True
    )
    
    with patch("app.fleet.get_db_context") as mock_get_context:
        mock_get_context.return_value.__enter__.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.all.return_value = [s1]
        
        loader = FleetLoader(mock_engine)
        await loader.load_fleet()
        
        # Should not start
        mock_engine.start_strategy.assert_not_called()
