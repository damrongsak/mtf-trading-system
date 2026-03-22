import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DriftMonitor:
    """
    Monitors market data for semantic and statistical drift.
    Triggers 'Safe Mode' if the current market distribution deviates significantly
    from the training/baseline distribution.
    """
    
    def __init__(self, baseline_mu: float = 0.0, baseline_sigma: float = 0.001):
        # Default baseline for XAU/USD 15m returns if not provided
        self.baseline_mu = baseline_mu
        self.baseline_sigma = baseline_sigma
        self.drift_threshold = 0.5 # KL Divergence threshold

    def calculate_kl_divergence(self, current_returns: pd.Series) -> float:
        """
        Calculates KL Divergence between Normal(baseline) and Normal(current).
        """
        if current_returns.empty or len(current_returns) < 20:
            return 0.0
            
        mu_curr = current_returns.mean()
        sigma_curr = current_returns.std()
        
        if sigma_curr == 0 or self.baseline_sigma == 0:
            return 0.0
            
        # KL Divergence for two univariate normal distributions
        term1 = np.log(self.baseline_sigma / sigma_curr)
        term2 = (sigma_curr**2 + (mu_curr - self.baseline_mu)**2) / (2 * self.baseline_sigma**2)
        kl_div = term1 + term2 - 0.5
        
        return float(max(0, kl_div))

    def check_drift(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform a drift check on the provided OHLC data.
        """
        if df.empty or len(df) < 50:
            return {"is_drifted": False, "kl_div": 0.0}
            
        # Calculate log returns
        returns = np.log(df['close'] / df['close'].shift(1)).dropna()
        
        kl_div = self.calculate_kl_divergence(returns)
        is_drifted = kl_div > self.drift_threshold
        
        if is_drifted:
            logger.warning(f"MARKET DRIFT DETECTED: KL Div = {kl_div:.4f} > Threshold {self.drift_threshold}")
            
        return {
            "is_drifted": is_drifted,
            "kl_div": kl_div,
            "threshold": self.drift_threshold,
            "current_mu": float(returns.mean()),
            "current_sigma": float(returns.std())
        }

# Singleton instance
monitor = DriftMonitor()
