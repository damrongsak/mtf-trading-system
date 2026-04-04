import math
from dataclasses import dataclass
from typing import Dict

@dataclass
class RiskAllocation:
    lot_size: float
    total_risk_amount: float
    is_authorized: bool = True

class DynamicRiskAllocator:
    """Calculates Lot Size based on mathematical precision."""

    def __init__(self, pips_per_unit: float = 0.01):
        self.pips_per_unit = pips_per_unit

    def calculate_lot_size(self, entry_price: float, stop_loss: float, equity: float, risk_percent: float) -> RiskAllocation:
        """
        Formula Logic (implied by spec):
        1. Risk Amount = Equity * Risk %
        2. Distance = abs(Entry - SL)
        3. Lot Size = Risk Amount / (Distance * PipValue)
        Constraint: Floor the lot size and verify margin.
        """
        risk_amount = equity * (risk_percent / 100)
        distance = abs(entry_price - stop_loss)
        
        if distance == 0:
            return RiskAllocation(0, 0, False)
        
        # Simple lot calculation (Placeholder for refined margin logic)
        raw_lot_size = risk_amount / (distance * 1000) # Assumes 1000 multiplier for gold/assets
        lot_size = math.floor(raw_lot_size * 100) / 100 # Floor to 2 decimal places

        return RiskAllocation(
            lot_size=max(0.01, lot_size),
            total_risk_amount=risk_amount
        )
