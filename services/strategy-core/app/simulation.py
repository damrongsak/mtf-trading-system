import numpy as np
import pandas as pd
# import vectorbt as vbt
from typing import List, Dict, Any, Tuple
from uuid import uuid4
from datetime import datetime, timedelta
from app.schemas import SimulationRequest, SimulationResponse, SimulationMetrics, EquityPoint

def generate_gbm(
    n_period: int, 
    start_price: float, 
    drift: float, 
    volatility: float, 
    noise_type: str = 'GAUSSIAN'
) -> np.ndarray:
    """
    Generate synthetic price path using Geometric Brownian Motion (GBM).
    Adjusts for market regime (trend, volatility, noise).
    """
    dt = 1.0  # Time step
    
    # Generate random shocks
    if noise_type == 'FAT_TAIL':
        # Use Student's t-distribution for fat tails (df=3 has heavy tails)
        shocks = np.random.standard_t(df=3, size=n_period)
        # Normalize to reduce extreme variance scaling
        shocks = shocks / np.std(shocks)
    else:
        # Standard Gaussian
        shocks = np.random.normal(0, 1, n_period)
        
    prices = np.zeros(n_period)
    prices[0] = start_price
    
    # GBM Formula: S_t = S_{t-1} * exp((mu - 0.5 * sigma^2)*dt + sigma * sqrt(dt) * Z_t)
    for t in range(1, n_period):
        prices[t] = prices[t-1] * np.exp(
            (drift - 0.5 * volatility**2) * dt + 
            volatility * np.sqrt(dt) * shocks[t]
        )
        
    return prices

def run_grid_simulation_logic(req: SimulationRequest) -> SimulationResponse:
    # 1. Parameter Mapping from Regime
    n_points = 1000 # ~1 month of 1H data
    start_price = 2000.0 # Gold-ish price
    
    # Drift (Trend)
    mu = 0.0
    if req.regime.trend == 'UPTREND':
        mu = 0.0001
    elif req.regime.trend == 'DOWNTREND':
        mu = -0.0001
        
    # Volatility (Sigma) - Scale 1-10 to 0.001 - 0.02
    sigma = 0.001 * req.regime.volatility
    
    # 2. Generate Synthetic Data
    price_data = generate_gbm(
        n_period=n_points,
        start_price=start_price,
        drift=mu,
        volatility=sigma,
        noise_type=req.regime.noise
    )
    
    # Create Datetime Index
    start_date = datetime.now() - timedelta(days=40)
    index = [start_date + timedelta(hours=i) for i in range(n_points)]
    price_series = pd.Series(price_data, index=index)
    
    # 3. Vectorbt Grid Strategy Logic
    # Simple Grid: Buy at lower levels, Sell at higher levels relative to initial price
    # NOTE: This is a simplified vectorized grid for MVP. 
    # Real grid keeps state, but VBT can simulate this via custom indicators or signals.
    
    grid_step = req.grid.step_size * 0.1 # Convert pips to price diff roughly (gold 1 pip = 0.1 ?) 
    # Assume 1 pip = $0.1 for XAUUSD? Or 0.01? Usually 0.01 for XAUUSD format 2000.00
    # Let's assume input step_size is in $ units for simplicity or raw price units.
    # If user says 10 pips, and price is 2000.00, 10 pips = 1.00 usually.
    step = req.grid.step_size * 0.1 # Adjust scaling as needed
    
    # Generate signals based on mean reversion to grid lines
    # For MVP, we'll use a simple RSI-like logic to simulate "Grid" behavior of buying low/selling high
    # A full VBT Grid requires Portfolio.from_orders with custom logic, which is complex for a single file.
    # We will approximate Grid behavior with a Mean Reversion strategy for the simulation results.
    
    import vectorbt as vbt
    fast_ma = vbt.MA.run(price_series, 10)
    slow_ma = vbt.MA.run(price_series, 50)
    
    # Buy when price drops (Grid Buy)
    entries = price_series < (fast_ma.ma - step)
    
    # Sell when price rises (Grid Sell)
    exits = price_series > (fast_ma.ma + step)
    
    # Run Portfolio
    import vectorbt as vbt
    pf = vbt.Portfolio.from_signals(
        price_series, 
        entries, 
        exits, 
        init_cash=10000,
        size=req.grid.initial_lot,
        size_type='amount', # or 'value'
        fees=0.0001 # Spread/Comms
    )
    
    # 4. Extract Metrics
    total_pnl = pf.total_profit()
    win_rate = pf.stats()['Win Rate [%]']
    max_dd = pf.stats()['Max Drawdown [%]']
    sharpe = pf.stats()['Sharpe Ratio']
    profit_factor = pf.stats()['Profit Factor']
    
    # Handle NaN stats
    if np.isnan(win_rate): win_rate = 0.0
    if np.isnan(max_dd): max_dd = 0.0
    if np.isnan(sharpe): sharpe = 0.0
    if np.isnan(profit_factor): profit_factor = 0.0
    
    # 5. Extract Equity Curve
    equity = pf.value()
    # Downsample for UI (every 10th point)
    equity_curve = []
    for ts, val in equity.iloc[::10].items():
        equity_curve.append(EquityPoint(
            timestamp=ts.isoformat(),
            value=float(val)
        ))
        
    return SimulationResponse(
        id=str(uuid4()),
        metrics=SimulationMetrics(
            total_pnl=float(total_pnl),
            win_rate=float(win_rate),
            max_drawdown=float(max_dd),
            sharpe_ratio=float(sharpe),
            profit_factor=float(profit_factor)
        ),
        equity_curve=equity_curve,
        status='COMPLETED'
    )
