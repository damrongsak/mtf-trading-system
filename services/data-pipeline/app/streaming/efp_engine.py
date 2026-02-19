import numpy as np
import numba
from typing import Optional

@numba.njit
def calculate_efp_spread(spot_bid: float, spot_ask: float, futures_bid: float, futures_ask: float) -> float:
    """
    Calculate the mid-price EFP spread with microsecond-level performance.
    EFP = Futures - Spot
    """
    spot_mid = (spot_bid + spot_ask) / 2.0
    futures_mid = (futures_bid + futures_ask) / 2.0
    return futures_mid - spot_mid

class EFPEngine:
    """
    High-performance engine for tracking EFP spread and calculating skews.
    Uses Numba-JIT for hot-path calculations.
    """
    def __init__(self, kappa_e: float = 8.0, sigma_e: float = 0.05, theta_e: float = 0.0):
        self.kappa_e = kappa_e
        self.sigma_e = sigma_e
        self.theta_e = theta_e
        self.last_spread = 0.0
        self.last_update_ts = 0.0

    def update(self, spot_bid: float, spot_ask: float, futures_bid: float, futures_ask: float, timestamp: float):
        self.last_spread = calculate_efp_spread(spot_bid, spot_ask, futures_bid, futures_ask)
        self.last_update_ts = timestamp
        return self.last_spread

    def get_state(self):
        return {
            "spread": self.last_spread,
            "timestamp": self.last_update_ts
        }
