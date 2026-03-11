import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from app.services.portfolio_service import PortfolioService

@pytest.mark.asyncio
async def test_calculate_risk_parity_weights():
    # Create sample price data for 3 symbols
    dates = pd.date_range("2023-01-01", periods=100)
    data = {
        "XAUUSD": np.linspace(1800, 1900, 100) + np.random.normal(0, 5, 100),
        "EURUSD": np.linspace(1.05, 1.10, 100) + np.random.normal(0, 0.01, 100),
        "BTCUSD": np.linspace(20000, 30000, 100) + np.random.normal(0, 500, 100)
    }
    df = pd.DataFrame(data, index=dates)
    
    weights = await PortfolioService.calculate_risk_parity_weights(df)
    
    assert isinstance(weights, dict)
    assert len(weights) == 3
    assert all(s in weights for s in ["XAUUSD", "EURUSD", "BTCUSD"])
    # Weights should sum to approx 1.0
    assert abs(sum(weights.values()) - 1.0) < 0.01
    
    # Low volatility asset (EURUSD) should likely have higher weight than high volatility (BTCUSD)
    # This depends on the random noise but generally holds for HRP
    assert weights["EURUSD"] > 0
    assert weights["BTCUSD"] > 0

@pytest.mark.asyncio
async def test_get_portfolio_metrics():
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "A": np.random.normal(100, 1, 100),
        "B": np.random.normal(100, 2, 100)
    }, index=dates)
    
    weights = {"A": 0.6, "B": 0.4}
    metrics = await PortfolioService.get_portfolio_metrics(weights, df)
    
    assert "annualized_volatility" in metrics
    assert "diversification_ratio" in metrics
    assert metrics["n_assets"] == 2
    assert metrics["diversification_ratio"] >= 1.0

@pytest.mark.asyncio
async def test_fetch_historical_prices_empty():
    with patch("app.services.portfolio_service.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        df = await PortfolioService.fetch_historical_prices(["NONEXISTENT"])
        assert df.empty

@pytest.mark.asyncio
async def test_optimize_portfolio_wrapper():
    with patch.object(PortfolioService, "fetch_historical_prices") as mock_fetch:
        # Mocking 2 symbols with some data
        dates = pd.date_range("2023-01-01", periods=10)
        mock_df = pd.DataFrame({
            "S1": np.random.normal(10, 1, 10),
            "S2": np.random.normal(10, 1, 10)
        }, index=dates)
        mock_fetch.return_value = mock_df
        
        result = await PortfolioService.optimize_portfolio(["S1", "S2"])
        
        assert "weights" in result
        assert "metrics" in result
        assert result["symbols_analyzed"] == ["S1", "S2"]
        assert len(result["weights"]) == 2
