import logging
import pandas as pd
from typing import Dict, Any, Optional
from app.quant.risk_map import risk_map_engine
from app.quant.positioning import positioning_engine


logger = logging.getLogger(__name__)

class QuantEngine:
    """
    Unified Quant Engine entry point.
    """

    def analyze(self, symbol: str, df: pd.DataFrame, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Unified analysis: Risk Map + Positioning suggestion.
        """
        risk_map = risk_map_engine.compute_risk_score(symbol, df, timeframe)
        return risk_map

    def calculate_sizing(self, 
                          symbol: str, 
                          df: pd.DataFrame, 
                          entry_price: float, 
                          stop_loss: float, 
                          equity: float, 
                          strategy_id: Optional[str] = None,
                          timeframe: str = "H1") -> Dict[str, Any]:
        """
        Unified sizing: Computes Risk Map first, then applies to Positioning Model.
        """
        risk_map = risk_map_engine.compute_risk_score(symbol, df, timeframe)
        
        if "error" in risk_map:
            return risk_map
            
        position_size = positioning_engine.calculate_lot_size(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            equity=equity,
            risk_map=risk_map,
            strategy_id=strategy_id
        )
        
        return {
            "risk_map": risk_map,
            "sizing": position_size
        }

quant_engine = QuantEngine()
