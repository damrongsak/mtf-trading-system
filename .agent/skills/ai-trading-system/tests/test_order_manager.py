import sys
import os
import unittest

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.executor.stratified_order_manager import StratifiedOrderManager

class TestOrderManager(unittest.TestCase):
    def setUp(self):
        self.manager = StratifiedOrderManager()

    def test_case_b_split(self):
        # Case: 0.1 total lot, Entry: 2350.5, SL: 2345.0, TP Major: 2360.0
        # Expected: 4 units of 0.025 lot
        orders = self.manager.create_case_b_orders(
            total_lot=0.1,
            entry=2350.5,
            sl=2345.0,
            tp_major=2360.0
        )
        self.assertEqual(len(orders), 4)
        for unit in orders:
            self.assertEqual(unit.lot_size, 0.025)

        # TP 1 should be at 1:1 RR distance (5.5 points from 2350.5) = 2356.0
        self.assertEqual(orders[0].tp, 2356.0)

    def test_breakeven_logic(self):
        # Setup orders
        self.manager.create_case_b_orders(0.1, 2350.5, 2345.0, 2360.0)
        
        # Manually set TP1 hit for one of the units (for testing)
        self.manager.positions[0].is_tp_hit = True
        
        # Trigger update (normally handled by price tracker)
        self.manager.update_automation(2356.0, 2350.5)
        
        # Check if units 3 and 4 have their SL at entry (2350.5)
        self.assertEqual(self.manager.positions[2].sl, 2350.5)
        self.assertTrue(self.manager.positions[2].is_sl_at_breakeven)

if __name__ == '__main__':
    unittest.main()
