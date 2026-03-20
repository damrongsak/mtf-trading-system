import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MinimaxRiskEngine:
    """
    Implements Minimax Regret logic for risk filtering.
    Evaluates the 'regret' of taking vs. not taking a signal based on historical 
    volatility and drawdown potential.
    """

    @staticmethod
    def calculate_regret(
        current_price: float,
        target_price: float,
        stop_loss: float,
        historical_volatility: float
    ) -> float:
        """
        Calculates the regret score. 
        Higher score = higher regret of NOT taking the trade (i.e. high conviction).
        """
        if stop_loss == current_price: return 0.0
        
        reward = abs(target_price - current_price)
        risk = abs(current_price - stop_loss)
        
        # Risk-Reward Ratio (RRR)
        rrr = reward / risk if risk > 0 else 0
        
        # Adjusted by Volatility (High vol = higher uncertainty = lower conviction)
        regret_score = (rrr / (historical_volatility + 1e-6))
        
        return float(regret_score)

    def filter_signal(self, signal: Dict[str, Any], threshold: float = 1.5) -> bool:
        """
        Returns True if the signal passes the minimax regret threshold.
        """
        entry = signal.get("entry_price")
        tp = signal.get("take_profit")
        sl = signal.get("stop_loss")
        vol = signal.get("metadata", {}).get("volatility", 0.01) # Default 1%
        
        if not all([entry, tp, sl]):
            return True # Cannot calculate, allow by default or block?
            
        score = self.calculate_regret(entry, tp, sl, vol)
        
        signal["metadata"]["minimax_regret_score"] = score
        
        if score < threshold:
            logger.info(f"Signal filtered by Minimax Regret: Score {score:.2f} < {threshold}")
            return False
            
        return True

minimax_engine = MinimaxRiskEngine()
