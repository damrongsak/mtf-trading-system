
import pytest
from app.simulation import run_grid_simulation_logic
from app.schemas import SimulationRequest, MarketRegime, GridConfig

def test_grid_simulation_basic():
    # Setup request
    regime = MarketRegime(
        trend="UPTREND",
        volatility=5,
        noise="GAUSSIAN"
    )
    grid = GridConfig(
        step_size=10.0,
        grid_levels=5,
        initial_lot=0.1,
        use_compound=False,
        stop_loss_pct=2.0
    )
    req = SimulationRequest(
        regime=regime,
        grid=grid,
        iterations=1
    )
    
    # Run
    res = run_grid_simulation_logic(req)
    
    # Assert
    assert res.status == "COMPLETED"
    assert len(res.equity_curve) > 0
    assert "total_pnl" in res.metrics.model_dump()
    assert res.metrics.sharpe_ratio is not None

def test_grid_simulation_no_trend():
    regime = MarketRegime(
        trend="NO_TREND",
        volatility=8,
        noise="FAT_TAIL"
    )
    grid = GridConfig(
        step_size=5.0,
        grid_levels=10,
        initial_lot=1.0,
        use_compound=True,
        stop_loss_pct=5.0
    )
    req = SimulationRequest(regime=regime, grid=grid, iterations=1)
    
    res = run_grid_simulation_logic(req)
    assert res.status == "COMPLETED"
    assert "equity_curve" in res.model_dump()
