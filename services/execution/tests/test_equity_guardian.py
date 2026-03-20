
import pytest
import json
import pandas as pd
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.equity_guardian import EquityGuardian, EquityCurveProjections
from app.models import Fund, BrokerAccount

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def guardian(mock_redis):
    # Mock Projections to return pre-defined dataframes
    with patch("app.services.equity_guardian.EquityCurveProjections") as mock_proj:
        g = EquityGuardian(mock_redis)
        g.projections = mock_proj
        return g

@pytest.mark.asyncio
async def test_calculate_metrics_hwm_recovery(guardian):
    """Verify that a recovered account shows zero current drawdown even if historical max DD was high."""
    # start_equity = 1000
    # trades: -10, -10, -10, -70, +200
    # curve: [1000, 990, 980, 970, 900, 1100]
    df = pd.DataFrame([
        {"timestamp": datetime(2026, 1, 1), "pnl": 0, "id": "1"}, 
        {"timestamp": datetime(2026, 1, 2), "pnl": -10, "id": "2"}, 
        {"timestamp": datetime(2026, 1, 3), "pnl": -10, "id": "3"},
        {"timestamp": datetime(2026, 1, 4), "pnl": -10, "id": "4"},
        {"timestamp": datetime(2026, 1, 5), "pnl": -70, "id": "5"}, # Max DD = -100
        {"timestamp": datetime(2026, 1, 6), "pnl": 200, "id": "6"}, # Recovery to new HWM (+100)
    ])
    
    # Calculate metrics
    metrics = guardian._calculate_metrics(df)
    
    assert metrics["max_drawdown_usd"] == -100.0
    assert metrics["current_drawdown_usd"] == 0.0 # Recovered!
    assert metrics["total_pnl"] == 100.0 
    assert metrics["current_hwm_usd"] == 100.0 

@pytest.mark.asyncio
async def test_calculate_metrics_current_drawdown(guardian):
    """Verify that current drawdown is correctly captured relative to recent HWM."""
    # start_equity = 1000
    # trades: +25, +25, +25, +25, -50
    # curve: [1000, 1025, 1050, 1075, 1100, 1050]
    df = pd.DataFrame([
        {"timestamp": datetime(2026, 1, 1), "pnl": 0, "id": "1"},
        {"timestamp": datetime(2026, 1, 2), "pnl": 25, "id": "2"},
        {"timestamp": datetime(2026, 1, 3), "pnl": 25, "id": "3"},
        {"timestamp": datetime(2026, 1, 4), "pnl": 25, "id": "4"},
        {"timestamp": datetime(2026, 1, 5), "pnl": 25, "id": "5"},
        {"timestamp": datetime(2026, 1, 6), "pnl": -50, "id": "6"},
    ])
    
    metrics = guardian._calculate_metrics(df)
    
    assert metrics["current_drawdown_usd"] == -50.0
    assert metrics["current_hwm_usd"] == 100.0

@pytest.mark.asyncio
async def test_check_risk_breach_trigger(guardian):
    """Verify that current DD breach triggers the hard stop."""
    metrics = {
        "total_pnl": 100.0,
        "current_hwm_usd": 100.0,   # High was +$100 (Total $1100)
        "current_drawdown_usd": -50.0 # Down $50 from high (Total $1050)
    }
    # DD Pct = (50 / 1100) * 100 = 4.54%
    
    fund = MagicMock(spec=Fund)
    fund.id = "fund-123"
    fund.max_drawdown_threshold = 4.0 # 4% limit
    
    account = MagicMock(spec=BrokerAccount)
    account.id = "acc-123"
    account.balance_snapshot = 1050.0 # Current Balance
    
    with patch("app.services.equity_guardian.AsyncSessionLocal") as mock_session_factory, \
         patch.object(guardian, "_trigger_hard_stop", new_callable=AsyncMock) as mock_halt:
        
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock result for stmt = select(Fund, BrokerAccount)...
        mock_result = MagicMock()
        mock_result.first.return_value = (fund, account)
        mock_session.execute.return_value = mock_result
        
        await guardian._check_risk_breach("acc-123", metrics)
        
        # Should trigger because 4.54% > 4.0%
        mock_halt.assert_called_once()
        args = mock_halt.call_args[0]
        assert "Current Drawdown % breach" in args[2]

@pytest.mark.asyncio
async def test_check_risk_breach_no_false_positive(guardian):
    """Verify that recovered account with high historical max DD does NOT trigger."""
    metrics = {
        "total_pnl": 100.0,
        "current_hwm_usd": 100.0,
        "current_drawdown_usd": 0.0, # Recovered!
        "max_drawdown_usd": -200.0  # Historical max DD was huge
    }
    
    fund = MagicMock(spec=Fund)
    fund.max_drawdown_threshold = 5.0
    
    account = MagicMock(spec=BrokerAccount)
    account.balance_snapshot = 1100.0
    
    with patch("app.services.equity_guardian.AsyncSessionLocal") as mock_session_factory, \
         patch.object(guardian, "_trigger_hard_stop", new_callable=AsyncMock) as mock_halt:
        
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.first.return_value = (fund, account)
        mock_session.execute.return_value = mock_result
        
        await guardian._check_risk_breach("acc-123", metrics)
        
        # Should NOT trigger
        mock_halt.assert_not_called()
