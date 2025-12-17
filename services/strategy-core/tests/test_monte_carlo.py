import pytest
from app.analysis.monte_carlo import run_monte_carlo

def test_monte_carlo_empty_trades():
    results = run_monte_carlo([])
    assert results == {}

def test_monte_carlo_basic_flow():
    # Mock trades: 10 wins of 1%, 10 losses of -0.5%
    trades = []
    for _ in range(10):
        trades.append({"return_pct": 0.01})
        trades.append({"return_pct": -0.005})
    
    # Run simulation
    metrics = run_monte_carlo(trades, n_sims=100)
    
    assert "iterations" in metrics
    assert metrics["iterations"] == 100
    assert "max_drawdown" in metrics
    assert "total_return" in metrics
    
    # Verify structure
    assert "p95" in metrics["max_drawdown"]
    assert "median" in metrics["max_drawdown"]
    assert "worst" in metrics["max_drawdown"]
    
    # Logic checks
    # Total return expected: (1.01^10 * 0.995^10) - 1 approx 0.05
    # P95/Median should not be none/inf
    assert metrics["total_return"]["median"] is not None

def test_monte_carlo_pnl_fallback():
    # Test fallback calculation if return_pct missing
    trades = [
        {"pnl": 100, "entry_price": 1000, "lot": 0.1}, # 100 / (1000 * 0.1 * 100000) ? No, lot size usually 100k units
        # Wait, implementation uses: (pnl) / (entry_price * lot * 100000)
        # 100 / (1000 * 0.1 * 100000) = 100 / 10,000,000 = 0.00001 (very small)
        # Let's adjust to be realistic: 1 Lot = 100k
        # PnL $1000 on 1 Lot EURUSD (price 1.0) -> 100 pips -> 1% move?
        # 1000 / (1.0 * 1.0 * 100000) = 0.01 = 1%
        {"pnl": 1000, "entry_price": 1.0, "lot": 1.0}
    ]
    
    metrics = run_monte_carlo(trades, n_sims=50)
    assert metrics["iterations"] == 50
