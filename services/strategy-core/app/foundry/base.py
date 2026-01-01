from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

class BlockType(str, Enum):
    TREND = "TREND"
    STRUCTURE = "STRUCTURE"
    MOMENTUM = "MOMENTUM"
    VOLATILITY = "VOLATILITY"

class SignalState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    INVALID = "INVALID"

class LogicBlock(ABC):
    """
    Abstract base class for all Strategy Foundry Logic Blocks.
    Each block is a reusable unit of trading logic.
    """
    
    def __init__(self, name: str, block_type: BlockType, parameters: Dict[str, Any] = None):
        """
        Initialize the logic block.
        :param name: Unique name of the block instance (e.g., "MainTrendEMA")
        :param block_type: Category (TREND, STRUCTURE, etc.)
        :param parameters: Configuration parameters (e.g., {"period": 200})
        """
        self.name = name
        self.block_type = block_type
        self.parameters = parameters or {}

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the logic block against the provided market context.
        
        :param context: Dictionary containing:
            - 'candles': DataFrame or Dict of candles for required timeframes
            - 'indicators': Pre-calculated indicators (optional)
        :return: Dictionary containing:
            - 'state': SignalState (BULLISH/BEARISH/NEUTRAL)
            - 'value': Raw value (e.g., RSI value, EMA value)
            - 'metadata': Any extra debug info
        """
        pass

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)
