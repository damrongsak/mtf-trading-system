import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class RLSignalFilter:
    """
    Institutional Signal Quality Filter.
    Uses a lightweight feature-based scoring (Proxy for RL) to classify 
    QM patterns as 'High Quality' or 'Low Quality'.
    
    Phase 2: Transition to a fully trained PPO/DQN model.
    """
    
    def __init__(self):
        # Weighting for different institutional features
        self.weights = {
            "displacement": 0.4,
            "session": 0.3,
            "atr_relative_range": 0.2,
            "rrr_potential": 0.1
        }
        
    def evaluate_pattern(self, ohlc_df: pd.DataFrame, pattern_data: Dict[str, Any], atr: float) -> Dict[str, Any]:
        """
        Evaluates a detected Quasimodo pattern.
        Returns a 'quality_score' (0.0 to 1.0) and a 'recommendation'.
        """
        try:
            # 1. Displacement Score (Magnitude of BOS)
            # Higher displacement = stronger institutional intent
            displacement_score = min(1.0, pattern_data.get('displacement_magnitude', 0) / 2.0)
            
            # 2. Session Score (ICT Killzones Proxy)
            # Gold is highly active in London/NY sessions
            current_hour = ohlc_df.index[-1].hour if isinstance(ohlc_df.index[-1], pd.Timestamp) else 0
            session_score = 0.5
            if 7 <= current_hour <= 10: # London Open
                session_score = 1.0
            elif 13 <= current_hour <= 17: # NY Open
                session_score = 1.0
            elif 0 <= current_hour <= 4: # Asian
                session_score = 0.3
                
            # 3. ATR Relative Range
            # We want patterns that are not too small (noise) or too large (overextended)
            pattern_range = pattern_data.get('range_pips', 0)
            atr_multiplier = pattern_range / atr if atr > 0 else 0
            atr_score = 0.0
            if 1.0 <= atr_multiplier <= 4.0:
                atr_score = 1.0
            elif atr_multiplier > 4.0:
                atr_score = 0.6 # Overextended
            else:
                atr_score = 0.3 # Too small
                
            # 4. RRR Potential
            rrr = pattern_data.get('rrr', 0)
            rrr_score = min(1.0, rrr / 3.0)
            
            # Weighted Composite Score
            final_score = (
                displacement_score * self.weights["displacement"] +
                session_score * self.weights["session"] +
                atr_score * self.weights["atr_relative_range"] +
                rrr_score * self.weights["rrr_potential"]
            )
            
            recommendation = "DISCARD"
            if final_score >= 0.7:
                recommendation = "HIGH_QUALITY"
            elif final_score >= 0.5:
                recommendation = "MEDIUM_QUALITY"
                
            return {
                "quality_score": round(final_score, 2),
                "recommendation": recommendation,
                "metrics": {
                    "displacement": displacement_score,
                    "session": session_score,
                    "atr_rel": atr_score,
                    "rrr": rrr_score
                }
            }
            
        except Exception as e:
            logger.error(f"Error in RLSignalFilter evaluation: {e}")
            return {"quality_score": 0.0, "recommendation": "ERROR"}

rl_filter = RLSignalFilter()
