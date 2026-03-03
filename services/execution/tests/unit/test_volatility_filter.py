import pytest
import json
from unittest.mock import AsyncMock, patch
from app.filters.volatility_filter import VolatilityFilter
from app.models import RiskFilter

@pytest.fixture
def mock_redis():
    with patch('app.filters.volatility_filter.get_redis_client') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client

def create_filter(params):
    f = RiskFilter()
    f.is_enabled = True
    f.threshold_parameters = params
    return f

@pytest.mark.asyncio
async def test_volatility_filter_pass(mock_redis):
    # Mock Redis returning low volatility
    mock_redis.get.return_value = json.dumps({"piv": {"volatility": 0.005}})
    
    filter_obj = VolatilityFilter()
    config = create_filter({"max_piv_volatility": 0.010})
    
    # Should pass since 0.005 < 0.010
    result = await filter_obj.validate(None, None, None, "XAUUSD", "LONG", 0, 0, 0, config)
    assert result == True

@pytest.mark.asyncio
async def test_volatility_filter_reject(mock_redis):
    # Mock Redis returning very high volatility
    mock_redis.get.return_value = json.dumps({"piv": {"volatility": 0.025}})
    
    filter_obj = VolatilityFilter()
    config = create_filter({"max_piv_volatility": 0.010})
    
    # Should reject since 0.025 > 0.010
    with pytest.raises(ValueError, match="PIV Volatility too high"):
         await filter_obj.validate(None, None, None, "XAUUSD", "LONG", 0, 0, 0, config)

@pytest.mark.asyncio
async def test_volatility_filter_no_cache(mock_redis):
    # Mock Redis returning nothing
    mock_redis.get.return_value = None
    
    filter_obj = VolatilityFilter()
    config = create_filter({"max_piv_volatility": 0.010})
    
    # Should pass by default if cache is empty to avoid blocking normal trading unnecessarily
    result = await filter_obj.validate(None, None, None, "XAUUSD", "LONG", 0, 0, 0, config)
    assert result == True
