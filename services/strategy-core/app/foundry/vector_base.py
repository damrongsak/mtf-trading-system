import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
import vectorbt as vbt
import logging

logger = logging.getLogger(__name__)

class VectorizedStrategyBase:
    """
    Standard base class for World-Class strategies using vectorbt.
    Supports both historical (vectorized) and live (iterative) execution.
    """
    
    def __init__(self, name: str, metadata: Dict[str, Any] = None):
        self.name = name
        self.metadata = metadata or {}

    def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
        """
        Execute strategy in vectorized mode (fast).
        Should return (entries, exits) as boolean series.
        """
        raise NotImplementedError("Subclasses must implement run_vector")

    def run_live(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Execute strategy on the latest bar for live signaling.
        Returns (direction, metadata).
        """
        # Default implementation: run vector and take the last signal
        entries, exits = self.run_vector(data, params)
        
        last_entry = entries.iloc[-1]
        last_exit = exits.iloc[-1]
        
        direction = None
        if last_entry: direction = "BULLISH"
        elif last_exit: direction = "FLAT"
        
        return direction, {"is_vector_derived": True}

    def simulate(self, data: pd.DataFrame, params: Dict[str, Any] = None, **kwargs) -> vbt.Portfolio:
        """
        Simulate portfolio performance.
        """
        entries, exits = self.run_vector(data, params)
        close = data['close']
        
        return vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            init_cash=kwargs.get('initial_capital', 10000),
            fees=kwargs.get('fees', 0.0001),
            slippage=kwargs.get('slippage', 0.0001),
            freq=kwargs.get('freq', '15T')
        )
