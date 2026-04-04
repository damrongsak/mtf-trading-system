from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class PositionUnit:
    id: int
    lot_size: float
    tp: float
    sl: float
    is_tp_hit: bool = False
    is_sl_at_breakeven: bool = False

class StratifiedOrderManager:
    """Strategy Case B: Split 4 units, TP1 -> Breakeven."""

    def __init__(self):
        self.positions: List[PositionUnit] = []

    def create_case_b_orders(self, total_lot: float, entry: float, sl: float, tp_major: float) -> List[PositionUnit]:
        """
        Divide total position into 4 units:
        Pos 1 & 2: TP at 1:1 RR or local swing.
        Pos 3 & 4: TP at major structural target.
        """
        unit_lot = total_lot / 4
        risk_dist = abs(entry - sl)
        tp_1 = entry + risk_dist if entry > sl else entry - risk_dist
        
        self.positions = [
            PositionUnit(id=1, lot_size=unit_lot, tp=tp_1, sl=sl),
            PositionUnit(id=2, lot_size=unit_lot, tp=tp_1, sl=sl),
            PositionUnit(id=3, lot_size=unit_lot, tp=tp_major, sl=sl),
            PositionUnit(id=4, lot_size=unit_lot, tp=tp_major, sl=sl)
        ]
        return self.positions

    def update_automation(self, current_price: float, entry: float):
        """Monitor TP1. Once hit, trigger BE logic for units 3 & 4."""
        tp1_hit = any(p.id in [1, 2] and p.is_tp_hit for p in self.positions)
        
        # Logic to check if price crossed TP1 (Simplified for spec demo)
        if not tp1_hit:
            # Check price...
            pass

        # Automation: Move SL of 3 & 4 to Entry Price (Break Even)
        for pos in self.positions:
            if pos.id in [3, 4] and not pos.is_sl_at_breakeven:
                pos.sl = entry
                pos.is_sl_at_breakeven = True
