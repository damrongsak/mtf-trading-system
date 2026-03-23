import pytest
import json
import uuid
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

# Mock settings before importing app components
import os
os.environ["REDIS_URL"] = "redis://redis:6379/0"

from app.services.portfolio_rebalancer import PortfolioRebalancer
from app.models import Fund, Strategy, PortfolioAllocation, BrokerAccount

@pytest.mark.asyncio
async def test_portfolio_rebalancer_full_flow():
    """
    Test the PortfolioRebalancer end-to-end with mocks.
    """
    # 1. Setup Mocks
    mock_db = AsyncMock()
    mock_rc = AsyncMock()
    
    # Mock Fund
    fund_id = uuid.uuid4()
    fund = Fund(
        id=fund_id,
        name="Test Quant Fund",
        risk_parity_enabled=True,
        risk_parity_model="HRP"
    )
    
    # Mock Strategies
    strat1_id = uuid.uuid4()
    strat2_id = uuid.uuid4()
    strat1 = Strategy(id=strat1_id, fund_id=fund_id, config_json={"symbol": "XAUUSD"}, is_active=True)
    strat2 = Strategy(id=strat2_id, fund_id=fund_id, config_json={"symbol": "EURUSD"}, is_active=True)
    
    # Mock DB Query results
    mock_db.execute.side_effect = [
        MagicMock(scalars=lambda: MagicMock(all=lambda: [fund])), # Funds
        MagicMock(scalars=lambda: MagicMock(all=lambda: [strat1, strat2])), # Strategies
        MagicMock(scalar_one_or_none=lambda: None), # Allocation 1 (None = Create new)
        MagicMock(scalar_one_or_none=lambda: None), # Allocation 2 (None = Create new)
    ]
    
    # Mock DataPipelineClient
    synthetic_candles = []
    for i in range(50):
        synthetic_candles.append({
            "timestamp": (datetime.now(timezone.utc)).isoformat(),
            "close": 100.0 + i
        })

    with patch("app.services.portfolio_rebalancer.DataPipelineClient") as MockClient, \
         patch("app.services.portfolio_rebalancer.get_redis_client", return_value=mock_rc), \
         patch("app.services.portfolio_rebalancer.AsyncSessionLocal", return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_db))):
        
        mock_pipeline = MockClient.return_value
        mock_pipeline.get_candles = AsyncMock(return_value=synthetic_candles)
        
        rebalancer = PortfolioRebalancer()
        # We need to manually pass our mock db to rebalance_fund or patch the session
        # The rebalance_all_funds creates its own session, so we patched AsyncSessionLocal above.
        
        await rebalancer.rebalance_all_funds()
        
        # 3. Assertions
        # Check if Redis was updated
        assert mock_rc.set.called, "Redis set was not called"
        args, kwargs = mock_rc.set.call_args
        assert f"fund:{fund_id}:risk_parity_weights" in args[0]
        
        weights = json.loads(args[1])
        assert "XAUUSD" in weights
        assert "EURUSD" in weights
        
        # Check if DB add was called for new allocations
        assert mock_db.add.called
        assert mock_db.commit.called
        
        print(f"\n✅ Portfolio Rebalancer Test Passed! Weights: {weights}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_portfolio_rebalancer_full_flow())
