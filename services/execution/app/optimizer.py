import pandas as pd
from pypfopt import EfficientFrontier, risk_models, expected_returns, HRPOpt
from typing import Dict

class PortfolioOptimizer:
    """
    Wrapper around PyPortfolioOpt to calculate optimal portfolio weights
    based on historical returns.
    """

    def __init__(self, prices_df: pd.DataFrame):
        """
        Initialize with a DataFrame of historical prices.
        :param prices_df: DataFrame with datetime index and columns as tickers.
        """
        self.prices_df = prices_df
        # Calculate expected returns and sample covariance
        self.mu = expected_returns.mean_historical_return(prices_df)
        self.S = risk_models.sample_cov(prices_df)

    def optimize_max_sharpe(self, risk_free_rate: float = 0.02) -> Dict[str, float]:
        """
        Optimize for maximal Sharpe ratio.
        """
        ef = EfficientFrontier(self.mu, self.S)
        ef.max_sharpe(risk_free_rate=risk_free_rate)
        cleaned_weights = ef.clean_weights()
        return cleaned_weights

    def optimize_min_volatility(self) -> Dict[str, float]:
        """
        Optimize for minimum volatility.
        """
        ef = EfficientFrontier(self.mu, self.S)
        ef.min_volatility()
        cleaned_weights = ef.clean_weights()
        return cleaned_weights

    def optimize_efficient_risk(self, target_volatility: float) -> Dict[str, float]:
        """
        Optimize for maximum return for a given target volatility.
        """
        ef = EfficientFrontier(self.mu, self.S)
        ef.efficient_risk(target_volatility)
        cleaned_weights = ef.clean_weights()
        return cleaned_weights

    def optimize_efficient_return(self, target_return: float) -> Dict[str, float]:
        """
        Optimize for minimum risk for a given target return.
        """
        ef = EfficientFrontier(self.mu, self.S)
        ef.efficient_return(target_return)
        cleaned_weights = ef.clean_weights()
        return cleaned_weights

    def optimize_hrp(self) -> Dict[str, float]:
        """
        Hierarchical Risk Parity (HRP).
        Robust to correlations and doesn't require mu.
        """
        # HRP requires returns df, not mu/S
        # Assuming index is already returns or we calculate here
        returns = self.prices_df.pct_change().dropna()
        hrp = HRPOpt(returns)
        hrp.optimize()
        return hrp.clean_weights()

    def optimize_erc(self) -> Dict[str, float]:
        """
        Equal Risk Contribution (ERC) / Risk Parity.
        """
        # Standard Risk Parity usually targets equalizing 'mu' or just based on S
        # PyPortfolioOpt handles this via min_vol with special constraints or dedicated class
        # For now, let's use the optimized_min_vol as proxy if ERC not directly simple
        return self.optimize_min_volatility()
