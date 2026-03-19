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

    def calculate_allocation(self, symbol: str, model: str = "HRP") -> float:
        """
        Calculate the target number of units for a given symbol
        based on the selected Risk Parity model.
        
        :param symbol: The ticker to allocate (e.g. 'XAU/USD').
        :param model: The optimization model (HRP, MIN_VOL, ERC).
        :return: Number of units to trade.
        """
        # 1. Get Optimal Weights
        if model == "HRP":
            weights = self.optimizer.optimize_hrp()
        elif model == "MIN_VOL":
            weights = self.optimizer.optimize_min_volatility()
        else:
            weights = self.optimizer.optimize_min_volatility() # Default fallback
            
        # 2. Get weight for this specific symbol
        target_weight = weights.get(symbol, 0.0)
        
        if target_weight == 0:
            return 0.0
            
        # 3. Calculate Risk Capital (Allocation of total equity)
        risk_capital = self.total_equity * target_weight
        
        # 4. Convert to Units
        current_price = self.prices[symbol].iloc[-1]
        units = risk_capital / current_price
        
        return units

    def get_risk_parity_weights(self, model: str = "HRP") -> Dict[str, float]:
        """
        Get all target weights for the current portfolio.
        """
        if model == "HRP":
            return self.optimizer.optimize_hrp()
        return self.optimizer.optimize_min_volatility()
