from typing import Dict, Any
import pandas as pd
from app.foundry.base import LogicBlock, BlockType, SignalState
from app.indicators import calculate_rsi

class MomentumRSICross(LogicBlock):
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.MOMENTUM, parameters)
        self.period = self.get_param("period", 14)
        self.timeframe = self.get_param("timeframe", "15m")
        self.cross_level = self.get_param("cross_level", 50)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None or len(candles) < self.period + 2:
            return {'state': SignalState.NEUTRAL, 'value': None}

        rsi = calculate_rsi(candles['close'], window=self.period)
        curr_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        state = SignalState.NEUTRAL
        
        # Bullish Cross: Prev < 50, Curr > 50
        if prev_rsi <= self.cross_level and curr_rsi > self.cross_level:
            state = SignalState.BULLISH
        # Bearish Cross: Prev > 50, Curr < 50
        elif prev_rsi >= self.cross_level and curr_rsi < self.cross_level:
            state = SignalState.BEARISH

        return {
            'state': state,
            'value': float(curr_rsi),
            'metadata': {'prev_rsi': float(prev_rsi)}
        }

    def run_vector(self, context: Dict[str, Any]) -> pd.Series:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None: return pd.Series()

        rsi = calculate_rsi(candles['close'], window=self.period)
        
        # shift(1) is Prev
        prev_rsi = rsi.shift(1)
        
        res = pd.Series(0, index=candles.index)
        
        # Bullish Cross
        res[(prev_rsi <= self.cross_level) & (rsi > self.cross_level)] = 1
        # Bearish Cross
        res[(prev_rsi >= self.cross_level) & (rsi < self.cross_level)] = -1
        
        return res

class MomentumVectorCandle(LogicBlock):
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, BlockType.MOMENTUM, parameters)
        self.timeframe = self.get_param("timeframe", "15m")
        self.rv_threshold = self.get_param("rv_threshold", 0.70)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None or len(candles) < 2:
            return {'state': SignalState.NEUTRAL, 'value': None}

        # Check Last Completed Candle (-2) or forming (-1)?
        # Spec says "Last Completed".
        candle = candles.iloc[-2]
        
        open_p = candle['open']
        close_p = candle['close']
        high = candle['high']
        low = candle['low']

        body = abs(close_p - open_p)
        total_range = high - low
        
        if total_range == 0:
            return {'state': SignalState.NEUTRAL}

        rv = body / total_range
        
        if rv >= self.rv_threshold:
            if close_p > open_p:
                 state = SignalState.BULLISH
            else:
                 state = SignalState.BEARISH
        else:
            state = SignalState.NEUTRAL

        return {
            'state': state,
            'value': float(rv),
            'metadata': {'threshold': self.rv_threshold}
        }

    def run_vector(self, context: Dict[str, Any]) -> pd.Series:
        candles = context.get('candles', {}).get(self.timeframe)
        if candles is None: return pd.Series()
        
        open_p = candles['open']
        close_p = candles['close']
        high = candles['high']
        low = candles['low']
        
        body = (close_p - open_p).abs()
        rng = high - low
        
        # Avoid div by zero
        rv = body / rng.replace(0, 1) # Simple safe div
        
        res = pd.Series(0, index=candles.index)
        
        # Green & High RV
        res[(rv >= self.rv_threshold) & (close_p > open_p)] = 1
        # Red & High RV
        res[(rv >= self.rv_threshold) & (close_p < open_p)] = -1
        
        return res
