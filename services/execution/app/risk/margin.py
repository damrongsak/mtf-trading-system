import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MarginCalculator:
    """
    Utility for calculating required margin based on account leverage.
    Formula: Required Margin = (Units * Entry Price) / Leverage
    """

    @staticmethod
    def calculate_required_margin(symbol: str, units: float, entry_price: float, leverage: int) -> float:
        """
        Calculates the required margin in account terms.
        
        Args:
            symbol: Trading instrument (e.g., 'XAU_USD', 'EUR_USD')
            units: Quantity of units (abs value used)
            entry_price: Market price or entry price
            leverage: Account leverage (e.g., 30, 1000)
            
        Returns:
            float: Required margin in the dominant currency of the pair.
        """
        if leverage <= 0:
            logger.warning(f"Invalid leverage {leverage} for {symbol}. Defaulting to 1:1 margin.")
            leverage = 1
            
        # Total Notional Value = Units * Entry Price
        # Note: units in mtf-trading-system are 'standard units' (e.g. 100,000 for 1.00 FX Lot)
        notional_value = abs(units) * entry_price
        
        required_margin = notional_value / float(leverage)
        
        logger.debug(f"Margin Calc: {symbol} | Units: {units} | Price: {entry_price} | Lev: 1:{leverage} | Margin: {required_margin:.2f}")
        return required_margin

    @staticmethod
    def can_afford(available_margin: float, required_margin: float, buffer_percent: float = 0.05) -> bool:
        """
        Checks if the account has enough available margin with an optional safety buffer.
        """
        buffered_required = required_margin * (1.0 + buffer_percent)
        return available_margin >= buffered_required
