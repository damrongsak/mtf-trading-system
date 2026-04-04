import sys
import os
import unittest

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.executor.dynamic_risk_allocator import DynamicRiskAllocator

class TestRiskAllocator(unittest.TestCase):
    def setUp(self):
        self.allocator = DynamicRiskAllocator()

    def test_lot_calculation(self):
        # Case: 10,000 equity, 1% risk ($100 risk)
        # Entry: 2350.5, SL: 2345.0 (5.5 point/distance)
        # Expected: Risk / (Dist * 1000) = 100 / (5.5 * 1000) = 100 / 5500 = 0.018...
        # Floor to 2 decimals = 0.01
        res = self.allocator.calculate_lot_size(
            entry_price=2350.5,
            stop_loss=2345.0,
            equity=10000.0,
            risk_percent=1.0
        )
        self.assertEqual(res.lot_size, 0.01)
        self.assertEqual(res.total_risk_amount, 100.0)

    def test_larger_risk(self):
        # Case: 10,000 equity, 5% risk ($500 risk)
        # Entry: 2350.5, SL: 2345.0 (5.5 distance)
        # Expected: 500 / 5500 = 0.0909...
        # Floor to 0.09
        res = self.allocator.calculate_lot_size(
            entry_price=2350.5,
            stop_loss=2345.0,
            equity=10000.0,
            risk_percent=5.0
        )
        self.assertEqual(res.lot_size, 0.09)

if __name__ == '__main__':
    unittest.main()
