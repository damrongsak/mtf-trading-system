import pytest
import json
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

# Mock settings before importing app components
import os
os.environ["REDIS_URL"] = "redis://redis:6379/0"

from app.risk.parity import RiskParityEngine

@pytest.mark.asyncio
async def test_sentiment_multiplier_alignment():
    """
    Test Ks multiplier when signal direction aligns with sentiment.
    """
    symbol = "XAUUSD"
    fund_id = str(uuid.uuid4())
    
    # Mock Redis sentiment: BULLISH (0.8)
    mock_rc = AsyncMock()
    mock_rc.get.return_value = json.dumps({"score": 0.8, "reason": "Strong gold demand"})
    
    # Mock Fund Cache: scale_factor 1.0
    mock_cache = AsyncMock()
    mock_cache.get_fund.return_value = {"scale_factor": 1.0}

    with patch("app.risk.parity.get_redis_client", return_value=mock_rc), \
         patch("app.services.cache_service.execution_cache", mock_cache):
        
        # Test 1: BUY + BULLISH -> Expect boost (1.0 + 0.8/4 = 1.20)
        km = 1.0
        multiplier = await RiskParityEngine.get_scale_multiplier(fund_id, symbol, "BUY", km)
        assert multiplier == 1.2
        
        # Test 2: SELL + BULLISH -> Expect protective cut (0.5)
        multiplier = await RiskParityEngine.get_scale_multiplier(fund_id, symbol, "SELL", km)
        assert multiplier == 0.5

@pytest.mark.asyncio
async def test_sentiment_multiplier_bearish_alignment():
    """
    Test Ks multiplier when signal direction aligns with BEARISH sentiment.
    """
    symbol = "EURUSD"
    fund_id = str(uuid.uuid4())
    
    # Mock Redis sentiment: BEARISH (-0.6)
    mock_rc = AsyncMock()
    mock_rc.get.return_value = json.dumps({"score": -0.6, "reason": "CPI miss"})
    
    mock_cache = AsyncMock()
    mock_cache.get_fund.return_value = {"scale_factor": 1.0}

    with patch("app.risk.parity.get_redis_client", return_value=mock_rc), \
         patch("app.services.cache_service.execution_cache", mock_cache):
        
        # Test 1: SELL + BEARISH -> Expect boost (1.0 + 0.6/4 = 1.15)
        multiplier = await RiskParityEngine.get_scale_multiplier(fund_id, symbol, "SHORT", 1.0)
        assert multiplier == 1.15
        
        # Test 2: BUY + BEARISH -> Expect cut (0.5)
        multiplier = await RiskParityEngine.get_scale_multiplier(fund_id, symbol, "LONG", 1.0)
        assert multiplier == 0.5

@pytest.mark.asyncio
async def test_sentiment_multiplier_neutral():
    """
    Test Ks multiplier when sentiment is neutral.
    """
    symbol = "BTCUSD"
    fund_id = str(uuid.uuid4())
    
    # Mock Redis sentiment: NEUTRAL (0.1)
    mock_rc = AsyncMock()
    mock_rc.get.return_value = json.dumps({"score": 0.1, "reason": "No news"})
    
    mock_cache = AsyncMock()
    mock_cache.get_fund.return_value = {"scale_factor": 1.0}

    with patch("app.risk.parity.get_redis_client", return_value=mock_rc), \
         patch("app.services.cache_service.execution_cache", mock_cache):
        
        multiplier = await RiskParityEngine.get_scale_multiplier(fund_id, symbol, "BUY", 1.0)
        assert multiplier == 1.0

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sentiment_multiplier_alignment())
