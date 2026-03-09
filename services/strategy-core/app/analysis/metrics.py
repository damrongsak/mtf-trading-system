import numpy as np
import pandas as pd
from typing import Union, Dict, Optional

def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.0, periods: int = 252) -> float:
    """
    Calculate annualized Sharpe Ratio.
    Sharpe = (Mean Return - Rf) / Std Dev
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    
    # Adjust Rf for the period frequency if provided as annual
    # Simple adjustment: Rf_daily = Rf_annual / periods
    rf_period = risk_free_rate / periods
    
    excess_returns = returns - rf_period
    return np.sqrt(periods) * (excess_returns.mean() / returns.std())

def calculate_sortino(returns: pd.Series, target_return: float = 0.0, periods: int = 252) -> float:
    """
    Calculate annualized Sortino Ratio.
    Sortino = (Mean Return - Target) / Downside Deviation
    """
    if returns.empty:
        return 0.0
        
    downside_returns = returns[returns < target_return]
    
    if downside_returns.empty or downside_returns.std() == 0:
        return 0.0
        
    downside_std = np.sqrt((downside_returns ** 2).mean()) # Lower Partial Moment (LPM) order 2
    
    if downside_std == 0:
        return 0.0
        
    # Annualized mean return
    mean_ret = returns.mean() * periods
    target_annual = target_return * periods
    
    return (mean_ret - target_annual) / (downside_std * np.sqrt(periods))

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate Maximum Drawdown (absolute percentage from peak).
    """
    if equity_curve.empty:
        return 0.0
        
    peaks = equity_curve.cummax()
    drawdowns = (equity_curve - peaks) / peaks
    return float(drawdowns.min())

def calculate_alpha_beta(returns: pd.Series, benchmark_returns: pd.Series, periods: int = 252) -> Dict[str, float]:
    """
    Calculate Alpha and Beta relative to a benchmark.
    Beta = Cov(Ra, Rb) / Var(Rb)
    Alpha = Ra - (Rf + Beta * (Rb - Rf))  -> Jensen's Alpha
    Simple Alpha = Ra - Beta * Rb (assuming Rf=0 for simplicity here or passed in)
    """
    if returns.empty or benchmark_returns.empty:
        return {"alpha": 0.0, "beta": 0.0}
        
    # Align data
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) < 2:
        return {"alpha": 0.0, "beta": 0.0}
        
    y = returns.loc[common_index].values
    x = benchmark_returns.loc[common_index].values
    
    # Covariance matrix
    covariance = np.cov(y, x)
    beta = covariance[0, 1] / covariance[1, 1]
    
    # Annualized Alpha (Jensen's approx assuming Rf=0 for differential)
    # alpha = (mean(y) - beta * mean(x)) * periods
    alpha = (np.mean(y) - beta * np.mean(x)) * periods
    
    return {"alpha": float(alpha), "beta": float(beta)}

def calculate_information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Calculate Information Ratio.
    IR = (Mean Active Return) / Tracking Error
    """
    if returns.empty or benchmark_returns.empty:
        return 0.0
        
    common_index = returns.index.intersection(benchmark_returns.index)
    if common_index.empty:
        return 0.0
    active_returns = returns.loc[common_index] - benchmark_returns.loc[common_index]
    
    if active_returns.std() == 0:
        return 0.0
        
    return float(active_returns.mean() / active_returns.std())

def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Calculate Value at Risk (VaR) using Historical Simulation.
    """
    if returns.empty:
        return 0.0
    return float(np.percentile(returns, (1 - confidence_level) * 100))

def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.
    """
    if returns.empty:
        return 0.0
    var = calculate_var(returns, confidence_level)
    tail_returns = returns[returns <= var]
    if tail_returns.empty:
        return var
    return float(tail_returns.mean())

def calculate_rolling_vol(returns: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Rolling Volatility.
    """
    if len(returns) < window:
        return pd.Series(dtype=float)
    return returns.rolling(window=window).std()

def calculate_parkinson_vol(high: pd.Series, low: pd.Series, window: int = 20) -> float:
    """
    Calculate Parkinson Volatility (High-Low range).
    """
    if len(high) < window or len(low) < window:
        return 0.0
    rs = np.log(high / low) ** 2
    vol = np.sqrt((1 / (4 * window * np.log(2))) * rs.rolling(window=window).sum())
    return float(vol.iloc[-1])

def calculate_rolling_beta(returns: pd.Series, benchmark_returns: pd.Series, window: int = 60) -> pd.Series:
    """
    Calculate Rolling Beta.
    """
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) < window:
        return pd.Series(dtype=float)
    
    y = returns.loc[common_index]
    x = benchmark_returns.loc[common_index]
    
    covariance = y.rolling(window=window).cov(x)
    variance = x.rolling(window=window).var()
    return covariance / variance

def calculate_rolling_momentum(returns: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Rolling Momentum (cumulative return over window).
    """
    if len(returns) < window:
        return pd.Series(dtype=float)
    return (1 + returns).rolling(window=window).apply(np.prod, raw=True) - 1
