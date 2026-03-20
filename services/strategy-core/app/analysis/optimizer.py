import pandas as pd
from pypfopt import EfficientFrontier, risk_models, expected_returns, HRPOpt
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Wrapper around PyPortfolioOpt to calculate optimal portfolio weights
    based on historical returns or prices.
    """

    def __init__(self, df: pd.DataFrame, is_returns: bool = False):
        """
        Initialize with a DataFrame of historical prices or returns.
        :param df: DataFrame with datetime index and columns as assets/strategies.
        :param is_returns: True if df contains returns, False if it contains prices.
        """
        self.df = df
        if isinstance(df, pd.Series):
             self.df = df.to_frame()

        if is_returns:
            self.returns = self.df
            # Approximate prices from returns for some PyPortfolioOpt methods if needed
            self.prices_df = (1 + self.returns).cumprod()
        else:
            self.prices_df = self.df
            self.returns = self.prices_df.pct_change().dropna()

        # Core Metrics
        try:
            self.mu = expected_returns.mean_historical_return(self.prices_df) if not is_returns else self.returns.mean() * 252
            self.S = risk_models.sample_cov(self.prices_df) if not is_returns else self.returns.cov() * 252
        except Exception as e:
            logger.error(f"Error calculating expected returns/cov: {e}")
            self.mu = None
            self.S = None

    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> Dict[str, float]:
        """Optimize for maximal Sharpe ratio."""
        if self.mu is None or self.S is None: return {}
        try:
            ef = EfficientFrontier(self.mu, self.S)
            ef.max_sharpe(risk_free_rate=risk_free_rate)
            return ef.clean_weights()
        except Exception as e:
            logger.warning(f"Max Sharpe optimization failed: {e}. Falling back to equal weight.")
            return self._equal_weights()

    def optimize_min_volatility(self) -> Dict[str, float]:
        """Optimize for minimum volatility."""
        if self.S is None: return {}
        try:
            ef = EfficientFrontier(self.mu, self.S)
            ef.min_volatility()
            return ef.clean_weights()
        except Exception as e:
            logger.warning(f"Min Volatility optimization failed: {e}.")
            return self._equal_weights()

    def optimize_hrp(self) -> Dict[str, float]:
        """Hierarchical Risk Parity (Robust, doesn't need mu)."""
        try:
            hrp = HRPOpt(self.returns)
            return hrp.optimize()
        except Exception as e:
            logger.error(f"HRP Optimization failed: {e}")
            return self._equal_weights()

    def _equal_weights(self) -> Dict[str, float]:
        n = len(self.df.columns)
        return {col: 1.0/n for col in self.df.columns}

    @classmethod
    def optimize_multi_strategy(cls, strategies_data: Dict[str, pd.Series], method: str = "HRP") -> Dict[str, float]:
        """
        Takes a dict of {strategy_id: equity_series} and returns optimal weights.
        """
        if not strategies_data: return {}
        
        # Align all series into a single DataFrame
        df = pd.DataFrame(strategies_data)
        df.sort_index(inplace=True)
        # Forward fill holes (holidays etc) then drop leading NaNs
        df = df.ffill().dropna()
        
        if df.empty or len(df) < 5:
            logger.warning("Insufficient data for multi-strategy optimization.")
            return {name: 1.0/len(strategies_data) for name in strategies_data.keys()}

        optimizer = cls(df, is_returns=False) # Data is Equity Curves (Prices)
        
        if method == "MAX_SHARPE":
            return optimizer.optimize_max_sharpe()
        elif method == "MIN_VOL":
            return optimizer.optimize_min_volatility()
        else:
            return optimizer.optimize_hrp()

