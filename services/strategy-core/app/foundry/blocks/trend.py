from typing import Dict, Any
import pandas as pd
from app.foundry.base import LogicBlock, BlockType, SignalState
from app.indicators import calculate_ema

class TrendEMACross(LogicBlock):
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.TREND, parameters)
        self.period = self.get_param("period", 200)
        self.timeframe = self.get_param("timeframe", "4h")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None or len(candles) < self.period + 1:
            return {'state': SignalState.NEUTRAL, 'value': None}

        ema = calculate_ema(candles['close'], span=self.period)
        last_close = candles['close'].iloc[-1]
        last_ema = ema.iloc[-1]

        state = SignalState.BULLISH if last_close > last_ema else SignalState.BEARISH
        
        return {
            'state': state,
            'value': float(last_ema),
            'metadata': {'close': float(last_close)}
        }

    def run_vector(self, context: Dict[str, Any]) -> pd.Series:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None:
            return pd.Series()
            
        ema = calculate_ema(candles['close'], span=self.period)
        
        # Vectorized comparison
        res = pd.Series(0, index=candles.index)
        res[candles['close'] > ema] = 1  # Bullish
        res[candles['close'] < ema] = -1 # Bearish
        return res

class TrendAMA(LogicBlock):
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.TREND, parameters)
        self.period = self.get_param("period", 10) # Efficiency Ratio period
        self.fast = self.get_param("fast", 2)
        self.slow = self.get_param("slow", 30)
        self.timeframe = self.get_param("timeframe", "4h")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None or len(candles) < self.period + 5:
            return {'state': SignalState.NEUTRAL, 'value': None}

        # Calculate KAMA using pandas_ta
        kama = candles.ta.kama(length=self.period, fast=self.fast, slow=self.slow)
        
        if kama is None or kama.empty:
             return {'state': SignalState.NEUTRAL, 'value': None}

        # Slope Check: Current vs Prev
        curr_kama = kama.iloc[-1]
        prev_kama = kama.iloc[-2]

        if curr_kama > prev_kama:
            state = SignalState.BULLISH
        elif curr_kama < prev_kama:
            state = SignalState.BEARISH
        else:
            state = SignalState.NEUTRAL

        return {
            'state': state,
            'value': float(curr_kama),
            'metadata': {'prev_value': float(prev_kama)}
        }

    def run_vector(self, context: Dict[str, Any]) -> pd.Series:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None:
             return pd.Series()

        kama = candles.ta.kama(length=self.period, fast=self.fast, slow=self.slow)
        if kama is None: return pd.Series()
        
        # Slope: Current > Prev
        diff = kama.diff()
        
        res = pd.Series(0, index=candles.index)
        res[diff > 0] = 1
        res[diff < 0] = -1
        return res
