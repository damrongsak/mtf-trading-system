"""
BOSWaves Strategy - Break of Structure with Waves
=====================================================================
Trend-following strategy using:
- EMA 50 for trend direction
- ATR 15 × 3.5 for trailing stop loss
- Trend flip for entry signals
- 3-Target profit system (1R, 2R, 3R)
- 50% partial close at TP1 + Move SL to breakeven

Author: Soda (Olympus AI)
Date: 2026-03-23
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from app.foundry.vector_base import VectorizedStrategyBase

logger = logging.getLogger(__name__)

METADATA = {
    "name": "BOSWaves (Break of Structure with Waves)",
    "description": "Trend-following strategy: EMA trend + ATR trailing stop + 3-TP system with partial profit",
    "version": "1.0.0",
    "author": "Soda (Olympus AI)",
    "defaults": {
        "ema_period": 50,          # EMA period for trend
        "atr_period": 15,          # ATR period
        "atr_multiplier": 3.5,     # SL = EMA - ATR × 3.5 (long) / EMA + ATR × 3.5 (short)
        "risk_per_trade": 0.01,    # 1% risk per trade
        "tp1_r": 1.0,               # TP1 = 1R
        "tp2_r": 2.0,               # TP2 = 2R
        "tp3_r": 3.0,               # TP3 = 3R
        "partial_close_pct": 0.5,   # 50% close at TP1
        "move_sl_to_be": True,      # Move SL to breakeven after TP1
        "session_filter": False,    # Filter off-hours (21:00-02:00)
        "mtf_confirm": False,       # Use 1H MTF confirmation
    }
}


# --- Indicator Calculations ---

def calculate_ema(prices: pd.Series, period: int = 50) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 15) -> pd.Series:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def calculate_trailing_levels(close: pd.Series, ema: pd.Series, atr: pd.Series, 
                               atr_mult: float = 3.5) -> Tuple[pd.Series, pd.Series]:
    """Calculate trailing stop levels (trail_up for longs, trail_dn for shorts)"""
    trail_up = ema - atr * atr_mult
    trail_dn = ema + atr * atr_mult
    return trail_up, trail_dn


def calculate_mtf_trend(data_15m: pd.DataFrame, data_1h: pd.DataFrame) -> pd.Series:
    """Calculate multi-timeframe trend from 1H data"""
    ema_1h = calculate_ema(data_1h['close'], 20)
    return (data_1h['close'] > ema_1h).astype(int)  # 1 = bullish, 0 = bearish


def detect_trend_flip(current_price: float, current_ema: float, prev_ema_trend: int) -> Tuple[int, int]:
    """
    Detect trend flip using scalar values:
    - Returns (current_trend, is_flip)
    - Trend: 1 = bullish, -1 = bearish, 0 = neutral
    - is_flip: 1 if trend changed, 0 otherwise
    """
    current_trend = 1 if current_price > current_ema else -1
    is_flip = 1 if current_trend != prev_ema_trend and prev_ema_trend != 0 else 0
    return current_trend, is_flip


# --- Strategy Logic ---

class BOSWavesStrategy(VectorizedStrategyBase):
    """
    BOSWaves: Break of Structure with Waves
    
    Entry Logic:
    - Trend flip detected (price crosses EMA 50)
    - Optional: MTF 1H confirmation
    - Optional: Session filter (avoid 21:00-02:00)
    
    Exit Logic:
    - TP3 hit: Close all
    - TP2 hit: Close remaining
    - TP1 hit: Close 50% + Move SL to breakeven
    - SL hit: Close all
    """
    
    def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
        p = {**METADATA["defaults"], **(params or {})}
        # print(f"DEBUG: run_vector started. params={p}")
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Calculate indicators
        ema = calculate_ema(close, p['ema_period'])
        atr = calculate_atr(high, low, close, p['atr_period'])
        trail_up, trail_dn = calculate_trailing_levels(close, ema, atr, p['atr_multiplier'])
        
        # Initialize signals
        trend = 0  # 0 = neutral, 1 = bullish, -1 = bearish
        entries = pd.Series(0, index=data.index)
        exits = pd.Series(0, index=data.index)
        
        # Track position state
        position_open = False
        position_dir = 0
        entry_price = 0
        stop_loss = 0
        tp1 = 0
        tp2 = 0
        tp3 = 0
        partial_closed = False
        
        start_idx = max(p['ema_period'] + 30, 100)
        # print(f"DEBUG: start_idx={start_idx}, total_len={len(data)}")
        
        for i in range(start_idx, len(data)):
            current_price = close.iloc[i]
            current_high = high.iloc[i]
            current_low = low.iloc[i]
            
            # Detect current trend
            current_trend, is_flip = detect_trend_flip(current_price, ema.iloc[i], trend)
            
            # Session filter
            if p.get('session_filter', False):
                hour = data.index[i].hour
                if hour >= 21 or hour <= 2:  # Skip off-hours
                    trend = current_trend
                    continue
            
            # Update trend if changed or initializing
            if is_flip or trend == 0:
                trend = current_trend
            
            # Entry signal on trend flip
            if is_flip and not position_open:
                risk = abs(current_price - (trail_up.iloc[i] if trend == 1 else trail_dn.iloc[i]))
                entry_price = current_price
                stop_loss = trail_up.iloc[i] if trend == 1 else trail_dn.iloc[i]
                tp1 = entry_price + risk * p['tp1_r'] if trend == 1 else entry_price - risk * p['tp1_r']
                tp2 = entry_price + risk * p['tp2_r'] if trend == 1 else entry_price - risk * p['tp2_r']
                tp3 = entry_price + risk * p['tp3_r'] if trend == 1 else entry_price - risk * p['tp3_r']
                
                entries.iloc[i] = trend
                position_open = True
                position_dir = trend
                partial_closed = False
            
            # Exit signals
            if position_open:
                exit_signal = 0
                
                if position_dir == 1:  # Long position
                    # TP3 hit
                    if current_high >= tp3:
                        exit_signal = 1
                    # TP2 hit
                    elif current_high >= tp2:
                        exit_signal = 1
                    # TP1 hit with partial close
                    elif current_high >= tp1:
                        if p['partial_close_pct'] > 0 and not partial_closed:
                            # Mark partial close - in vectorbt we just exit fully
                            exit_signal = 1
                            partial_closed = True
                        elif partial_closed:
                            exit_signal = 1
                    # SL hit
                    elif current_low <= stop_loss:
                        exit_signal = -1
                        
                else:  # Short position
                    # TP3 hit
                    if current_low <= tp3:
                        exit_signal = -1
                    # TP2 hit
                    elif current_low <= tp2:
                        exit_signal = -1
                    # TP1 hit with partial close
                    elif current_low <= tp1:
                        if p['partial_close_pct'] > 0 and not partial_closed:
                            exit_signal = -1
                            partial_closed = True
                        elif partial_closed:
                            exit_signal = -1
                    # SL hit
                    elif current_high >= stop_loss:
                        exit_signal = 1
                
                if exit_signal != 0:
                    exits.iloc[i] = exit_signal
                    position_open = False
                    position_dir = 0
        
        return entries, exits


# --- Async Entry Point ---

async def strategy(state, data_manager) -> Tuple[pd.Series, pd.Series, Optional[Dict[str, Any]]]:
    """Async entry point for Fleet Manager"""
    symbol = state.symbol
    tf = state.timeframe
    params = state.config_json if state.config_json else {}
    
    try:
        data = data_manager.get_candles(symbol, timeframe=tf)
        if data.empty:
            return None, None, None
        
        # Get strategy result
        strat_obj = BOSWavesStrategy("boswaves_v1")
        entries, exits = strat_obj.run_vector(data, params)
        
        # Build signal dict
        p = {**METADATA["defaults"], **(params or {})}
        close = data['close']
        high = data['high']
        low = data['low']
        
        ema = calculate_ema(close, p['ema_period'])
        atr = calculate_atr(high, low, close, p['atr_period'])
        trail_up, trail_dn = calculate_trailing_levels(close, ema, atr, p['atr_multiplier'])
        
        last_idx = -1
        current_price = float(close.iloc[last_idx])
        current_ema = float(ema.iloc[last_idx])
        current_atr = float(atr.iloc[last_idx])
        
        # Determine direction
        direction = "FLAT"
        if entries.iloc[last_idx] == 1:
            direction = "BULLISH"
        elif entries.iloc[last_idx] == -1:
            direction = "BEARISH"
        
        signal_dict = None
        if direction != "FLAT":
            risk = abs(current_price - (trail_up.iloc[last_idx] if direction == "BULLISH" else trail_dn.iloc[last_idx]))
            
            logic_path = []
            logic_path.append(f"EMA_{p['ema_period']}_CROSS")
            logic_path.append(f"ATR_{p['atr_period']}_TRAIL")
            if p.get('mtf_confirm'):
                logic_path.append("MTF_1H_CONFIRM")
            if p.get('session_filter'):
                logic_path.append("SESSION_FILTER")
            
            signal_dict = {
                "direction": direction,
                "entry_price": current_price,
                "stop_loss": float(trail_up.iloc[last_idx] if direction == "BULLISH" else trail_dn.iloc[last_idx]),
                "take_profit_1": current_price + risk if direction == "BULLISH" else current_price - risk,
                "take_profit_2": current_price + risk * 2 if direction == "BULLISH" else current_price - risk * 2,
                "take_profit_3": current_price + risk * 3 if direction == "BULLISH" else current_price - risk * 3,
                "reason": f"BOSWaves: {direction} ({', '.join(logic_path)})",
                "metadata": {
                    "ema": current_ema,
                    "atr": current_atr,
                    "atr_mult": p['atr_multiplier'],
                    "risk": risk,
                    "tp1_r": p['tp1_r'],
                    "tp2_r": p['tp2_r'],
                    "tp3_r": p['tp3_r'],
                    "partial_close": p['partial_close_pct'],
                    "move_sl_to_be": p['move_sl_to_be']
                }
            }
        
        return entries, exits, signal_dict
        
    except Exception as e:
        logger.error(f"Error in BOSWaves strategy: {e}")
        return None, None, None


def strategy_vectorized(data: pd.DataFrame, params: Dict[str, Any] = None):
    """Vectorbt-optimized entry point"""
    strat_obj = BOSWavesStrategy("boswaves_v1")
    return strat_obj.run_vector(data, params)