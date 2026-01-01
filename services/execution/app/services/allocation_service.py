import pandas as pd
from typing import Dict
from app.optimizer import PortfolioOptimizer

class AllocationService:
    """
    Service to determine trade sizing based on Portfolio Risk Parity.
    Uses PyPortfolioOpt to calculate optimal weights.
    """

    def __init__(self, historical_prices: pd.DataFrame, total_equity: float):
        """
        :param historical_prices: DataFrame of OHLCV (Close prices) for portfolio assets.
        :param total_equity: Current total account equity.
        """
        self.prices = historical_prices
        self.total_equity = total_equity
        self.optimizer = PortfolioOptimizer(historical_prices)

    def calculate_allocation(self, symbol: str) -> float:
        """
        Calculate the target number of units for a given symbol
        based on Minimum Volatility (Risk Parity approach).
        
        :param symbol: The ticker to allocate (e.g. 'XAU/USD').
        :return: Number of units to trade.
        """
        # 1. Get Optimal Weights (Min Volatility = Risk Parity approximation)
        weights = self.optimizer.optimize_min_volatility()
        
        # 2. Get weight for this specific symbol
        # Map symbol if necessary (e.g. XAU/USD -> XAUUSD)
        target_weight = weights.get(symbol, 0.0)
        
        if target_weight == 0:
            return 0.0
            
        # 3. Calculate Risk Capital
        risk_capital = self.total_equity * target_weight
        
        # 4. Convert to Units
        current_price = self.prices[symbol].iloc[-1]
        units = risk_capital / current_price
        
        return units

    def get_risk_parity_weights(self) -> Dict[str, float]:
        """
        Get all target weights for the current portfolio.
        """
        return self.optimizer.optimize_min_volatility()
