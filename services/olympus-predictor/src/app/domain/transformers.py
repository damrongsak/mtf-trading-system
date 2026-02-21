import numpy as np
import pandas as pd

class LogReturnTransformer:
    """
    Utility to transform absolute prices into log-returns and back.
    Formula: r_t = ln(P_t / P_{t-1})
    """
    
    @staticmethod
    def transform(series: pd.Series) -> pd.Series:
        """Calculate log-returns"""
        return np.log(series / series.shift(1)).dropna()

    @staticmethod
    def inverse_transform(last_price: float, returns: np.ndarray) -> np.ndarray:
        """
        Convert log-returns back to absolute prices.
        P_t = P_{t-1} * exp(r_t)
        """
        cumulative_returns = np.cumsum(returns)
        prices = last_price * np.exp(cumulative_returns)
        return prices
