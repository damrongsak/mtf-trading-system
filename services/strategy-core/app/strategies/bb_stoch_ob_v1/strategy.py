"""
BB_Stochastic_OB - Bollinger Bands + Stochastic + Order Block Strategy
=====================================================================
A professional-grade trading strategy combining:
- Bollinger Bands (13, 1.5) for volatility-based entries
- Stochastic Oscillator (9, 3, 3) for momentum confirmation
- Order Block (SMC) for institutional footprint confirmation

Author: Soda (Olympus AI)
Date: 2026-03-18
Upgrade: Vectorized (v2.8)
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any, Union
import vectorbt as vbt
from app.foundry.vector_base import VectorizedStrategyBase

logger = logging.getLogger(__name__)

METADATA = {
    "name": "BB Stochastic Order Block (SMC)",
    "description": "Mean Reversion with Order Block Confirmation - Buy/Sell at BB extremes + Stoch exhaustion + OB zone confirmation",
    "version": "2.8.0",
    "author": "Soda (Olympus AI)",
    "defaults": {
        "bb_period": 13,
        "bb_std": 1.5,
        "stoch_k": 9,
        "stoch_d": 3,
        "stoch_oversold": 20,
        "stoch_overbought": 80,
        "ob_lookback": 15,
        "ob_tolerance": 0.008,  # 0.8% price tolerance for OB zones
        "risk_per_trade": 0.01,  # 1% risk per trade
        "atr_multiplier": 2.0    # ATR-based stop loss
    }
}

# --- Standard Logic Helpers ---

def calculate_bollinger_bands(prices: pd.Series, period: int = 13, std_dev: float = 1.5) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return sma, upper_band, lower_band


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 9, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator (%K and %D)"""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    # Avoid division by zero
    diff = (highest_high - lowest_low)
    k = 100 * (close - lowest_low) / diff.replace(0, np.nan)
    d = k.rolling(window=d_period).mean()
    
    return k, d


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def find_order_blocks(open_prices: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 15) -> list:
    """Find Order Blocks (SMC concept)"""
    order_blocks = []
    for i in range(lookback + 5, len(close) - 3):
        # Bullish Order Block
        if close.iloc[i] < open_prices.iloc[i]:  # Bear candle
            if close.iloc[i+1] > open_prices.iloc[i+1] and close.iloc[i+2] > open_prices.iloc[i+2]:
                if high.iloc[i+2] > high.iloc[i]:
                    order_blocks.append({"type": "BULLISH", "high": high.iloc[i], "low": low.iloc[i], "index": i})
        # Bearish Order Block
        elif close.iloc[i] > open_prices.iloc[i]:  # Bull candle
            if close.iloc[i+1] < open_prices.iloc[i+1] and close.iloc[i+2] < open_prices.iloc[i+2]:
                if low.iloc[i+2] < low.iloc[i]:
                    order_blocks.append({"type": "BEARISH", "high": high.iloc[i], "low": low.iloc[i], "index": i})
    return order_blocks


def get_ob_signals(data: pd.DataFrame, lookback: int = 15, tolerance: float = 0.008) -> Tuple[pd.Series, pd.Series]:
    """Vectorized-ish OB detection (pre-calculated per bar)"""
    bullish_ob_active = pd.Series(False, index=data.index)
    bearish_ob_active = pd.Series(False, index=data.index)
    
    # This remains iterative because OB detection is pattern-based
    obs = find_order_blocks(data['open'], data['high'], data['low'], data['close'], lookback)
    
    # Map OB zones to time series
    for ob in obs:
        idx = ob['index']
        # Active from the moment it's identified until end or mitigation (simplified: active for N bars)
        # We check price near this zone for the next 100 bars or until end
        end_search = min(idx + 100, len(data))
        for j in range(idx + 2, end_search):
            price = data['close'].iloc[j]
            if ob['type'] == "BULLISH":
                if abs(price - ob['low']) / price < tolerance or abs(price - ob['high']) / price < tolerance:
                    bullish_ob_active.iloc[j] = True
            else:
                if abs(price - ob['low']) / price < tolerance or abs(price - ob['high']) / price < tolerance:
                    bearish_ob_active.iloc[j] = True
                    
    return bullish_ob_active, bearish_ob_active

# --- World-Class Class Implementation ---

class BBStochOBStrategy(VectorizedStrategyBase):
    def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
        p = {**METADATA["defaults"], **(params or {})}
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Indicators
        _, bb_upper, bb_lower = calculate_bollinger_bands(close, p['bb_period'], p['bb_std'])
        stoch_k, _ = calculate_stochastic(high, low, close, p['stoch_k'], p['stoch_d'])
        bull_ob, bear_ob = get_ob_signals(data, p['ob_lookback'], p['ob_tolerance'])
        
        # Entry Logic
        long_entries = (close < bb_lower) & (stoch_k < p['stoch_oversold']) & bull_ob
        short_entries = (close > bb_upper) & (stoch_k > p['stoch_overbought']) & bear_ob
        
        # Exit Logic
        long_exits = (close > bb_upper) | (stoch_k > p['stoch_overbought'])
        short_exits = (close < bb_lower) | (stoch_k < p['stoch_oversold'])
        
        # Combined Signals (long = 1, short = -1)
        entries = pd.Series(0, index=data.index)
        entries[long_entries] = 1
        entries[short_entries] = -1
        
        exits = pd.Series(0, index=data.index)
        exits[long_exits] = 1
        exits[short_exits] = -1
        
        return entries, exits

# --- API Compatibility Functions ---

def strategy(data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series, Dict[str, Any]]:
    """Standard entry point for backtest engine with rich learnable metadata."""
    strat_obj = BBStochOBStrategy("bb_stoch_ob_v1")
    entries, exits = strat_obj.run_vector(data, params)
    
    # Generate live signal dictionary from last row with RICH features
    p = {**METADATA["defaults"], **(params or {})}
    close = data['close']
    high = data['high']
    low = data['low']
    
    last_idx = -1
    current_price = float(close.iloc[last_idx])
    
    # Re-calculate indicator values for the last bar to include in metadata
    _, bb_upper, bb_lower = calculate_bollinger_bands(close, p['bb_period'], p['bb_std'])
    stoch_k, stoch_d = calculate_stochastic(high, low, close, p['stoch_k'], p['stoch_d'])
    bull_ob, bear_ob = get_ob_signals(data, p['ob_lookback'], p['ob_tolerance'])
    atr = calculate_atr(high, low, close)
    
    direction = "FLAT"
    if entries.iloc[last_idx] == 1: direction = "BULLISH"
    elif entries.iloc[last_idx] == -1: direction = "BEARISH"
    
    # Build Logic Confluence Path
    logic_path = []
    if current_price < bb_lower.iloc[last_idx]: logic_path.append("BB_OVERSOLD")
    if current_price > bb_upper.iloc[last_idx]: logic_path.append("BB_OVERBOUGHT")
    if stoch_k.iloc[last_idx] < p['stoch_oversold']: logic_path.append("STOCH_OVERSOLD")
    if stoch_k.iloc[last_idx] > p['stoch_overbought']: logic_path.append("STOCH_OVERBOUGHT")
    if bull_ob.iloc[last_idx]: logic_path.append("BULLISH_OB_ZONE")
    if bear_ob.iloc[last_idx]: logic_path.append("BEARISH_OB_ZONE")

    signal_dict = {
        "direction": direction,
        "entry_price": current_price,
        "reason": f"Signal via {', '.join(logic_path)}" if logic_path else "No clear confluence",
        "metadata": {
            "strategy_version": "2.8.0-vectorized",
            "logic_path": logic_path,
            # Learnable Features
            "features": {
                "bb_upper": float(bb_upper.iloc[last_idx]),
                "bb_lower": float(bb_lower.iloc[last_idx]),
                "bb_width_pct": float((bb_upper.iloc[last_idx] - bb_lower.iloc[last_idx]) / current_price * 100),
                "stoch_k": float(stoch_k.iloc[last_idx]),
                "stoch_d": float(stoch_d.iloc[last_idx]),
                "atr": float(atr.iloc[last_idx]),
                "price_to_bb_lower_ratio": float(current_price / bb_lower.iloc[last_idx]),
                "price_to_bb_upper_ratio": float(current_price / bb_upper.iloc[last_idx])
            },
            "smc_context": {
                "in_bullish_ob": bool(bull_ob.iloc[last_idx]),
                "in_bearish_ob": bool(bear_ob.iloc[last_idx])
            }
        }
    }
    
    return entries, exits, signal_dict

def strategy_vectorized(data: pd.DataFrame, params: Dict[str, Any] = None):
    """Vectorbt-optimized entry point."""
    strat_obj = BBStochOBStrategy("bb_stoch_ob_v1")
    return strat_obj.run_vector(data, params)
