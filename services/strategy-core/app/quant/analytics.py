import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from app.market_data import market_data_manager
from app.analysis import metrics

class QuantAnalyticsEngine:
    """
    Orchestrator for Quantitative Analytics.
    Fetches OHLCV data, calculates returns, and computes metrics.
    """

    def __init__(self):
        self.mdm = market_data_manager

    def get_returns(self, symbol: str, timeframe: str = "H1", limit: int = 500) -> pd.Series:
        """Fetch candles and calculate log returns."""
        df = self.mdm.get_candles(symbol, timeframe, limit)
        if df.empty or 'close' not in df.columns:
            return pd.Series(dtype=float)
        return np.log(df['close'] / df['close'].shift(1)).dropna()

    def get_volatility_metrics(self, symbol: str, timeframe: str = "H1", limit: int = 500) -> Dict[str, Any]:
        """Calculate various volatility metrics."""
        df = self.mdm.get_candles(symbol, timeframe, limit)
        if df.empty:
            return {}

        returns = np.log(df['close'] / df['close'].shift(1)).dropna()
        realized_vol = returns.std() * np.sqrt(252) if not returns.empty else 0.0
        
        parking_vol = metrics.calculate_parkinson_vol(df['high'], df['low'], window=20)
        rolling_vol = metrics.calculate_rolling_vol(returns, window=20)

        return {
            "realized_vol": float(realized_vol),
            "parkinson_vol": float(parking_vol),
            "yang_zhang_vol": 0.0,  # Placeholder for complex YZ vol if needed
            "rolling_vol_series": rolling_vol.dropna().tolist()
        }

    def get_var_metrics(self, symbol: str, timeframe: str = "H1", limit: int = 500) -> Dict[str, Any]:
        """Calculate VaR and CVaR metrics."""
        returns = self.get_returns(symbol, timeframe, limit)
        if returns.empty:
            return {}

        return {
            "var_95": metrics.calculate_var(returns, 0.95),
            "var_99": metrics.calculate_var(returns, 0.99),
            "cvar_95": metrics.calculate_cvar(returns, 0.95),
            "cvar_99": metrics.calculate_cvar(returns, 0.99)
        }

    def get_factor_exposures(self, symbol: str, timeframe: str = "H1", limit: int = 500) -> Dict[str, Any]:
        """Calculate factor exposures (Beta, Momentum, etc.)."""
        returns = self.get_returns(symbol, timeframe, limit)
        if returns.empty:
            return {}

        # For Beta, we need a benchmark. Defaulting to SPX or similar if available in MDM.
        # For now, placeholder or self-beta (1.0).
        beta = 1.0 
        momentum = metrics.calculate_rolling_momentum(returns, window=20).iloc[-1] if len(returns) >= 20 else 0.0
        
        # Simple volatility regime: High if current vol > 1.5 * historical mean
        vol_series = metrics.calculate_rolling_vol(returns, window=20)
        regime = "NORMAL"
        if not vol_series.empty:
            current_vol = vol_series.iloc[-1]
            mean_vol = vol_series.mean()
            if current_vol > mean_vol * 1.5:
                regime = "HIGH"
            elif current_vol < mean_vol * 0.5:
                regime = "LOW"

        return {
            "beta": float(beta),
            "momentum": float(momentum),
            "rsi": 0.0,  # Could add RSI from indicators
            "volatility_regime": regime
        }

    def get_drawdown_metrics(self, symbol: str, timeframe: str = "H1", limit: int = 500) -> Dict[str, Any]:
        """Calculate drawdown metrics."""
        df = self.mdm.get_candles(symbol, timeframe, limit)
        if df.empty:
            return {}

        equity_curve = df['close'] # Treating price as equity for asset-level DD
        max_dd = metrics.calculate_max_drawdown(equity_curve)
        
        # Current DD
        peak = equity_curve.max()
        current_val = equity_curve.iloc[-1]
        current_dd = (current_val - peak) / peak

        return {
            "max_drawdown": float(max_dd),
            "current_drawdown": float(current_dd),
            "dd_duration": 0, # Placeholder
            "recovery_factor": 0.0 # Placeholder
        }

analytics_engine = QuantAnalyticsEngine()
