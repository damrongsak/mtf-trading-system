import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class LiquidityAnalyzer:
    """
    Professional Liquidity Analyzer for SMC Strategies.
    Focuses on:
    1. Fractal Swing Points (3-5 bar window)
    2. Liquidity Grabs (Small wick penetration + close back)
    3. Liquidity Sweeps (Powerful push through levels)
    """

    def __init__(self, fractal_window: int = 5):
        self.fractal_window = fractal_window

    def find_swing_points(self, df: pd.DataFrame, window: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identifies Swing Highs and Swing Lows using Fractal logic.
        """
        w = window or self.fractal_window
        highs = []
        lows = []
        
        for i in range(w, len(df) - w):
            # Check for Swing High (Fractal)
            # Center point must be higher than 'w' points before and after
            is_high = True
            for j in range(1, w + 1):
                if df['high'].iloc[i] <= df['high'].iloc[i-j] or df['high'].iloc[i] <= df['high'].iloc[i+j]:
                    is_high = False
                    break
            
            if is_high:
                highs.append({
                    "index": i,
                    "time": df.index[i],
                    "price": df['high'].iloc[i],
                    "type": "BSL" # Buy Side Liquidity
                })

            # Check for Swing Low (Fractal)
            is_low = True
            for j in range(1, w + 1):
                if df['low'].iloc[i] >= df['low'].iloc[i-j] or df['low'].iloc[i] >= df['low'].iloc[i+j]:
                    is_low = False
                    break
            
            if is_low:
                lows.append({
                    "index": i,
                    "time": df.index[i],
                    "price": df['low'].iloc[i],
                    "type": "SSL" # Sell Side Liquidity
                })
        
        return {"highs": highs, "lows": lows}

    def detect_liquidity_grabs(self, df: pd.DataFrame, pivots: Dict[str, List[Dict[str, Any]]], lookback: int = 50) -> List[Dict[str, Any]]:
        """
        Detects Liquidity Grabs (Swing Failure Patterns - SFP).
        Logic:
        1. Price pierces a recent Pivot (BSL/SSL) with its wick.
        2. Candle MUST close back inside (below BSL for Bullish Grab, above SSL for Bearish Grab).
        """
        grabs = []
        current_idx = len(df) - 1
        
        # We only check the last completed candle (index -1)
        candle = df.iloc[-1]
        
        # 1. Bullish Trap (Sweeping BSL then Reversing) -> Bearish Signal
        for p in pivots['highs']:
            # Only look at pivots within lookback and BEFORE current candle
            if p['index'] < current_idx - 1 and p['index'] > current_idx - lookback:
                # Did high pierce BSL but close below?
                if candle['high'] > p['price'] and candle['close'] < p['price']:
                    grabs.append({
                        "type": "bearish_grab",
                        "pivot_price": p['price'],
                        "time": df.index[-1],
                        "description": f"Liquidated BSL at {p['price']:.2f} (Bearish SFP)"
                    })

        # 2. Bearish Trap (Sweeping SSL then Reversing) -> Bullish Signal
        for p in pivots['lows']:
            if p['index'] < current_idx - 1 and p['index'] > current_idx - lookback:
                # Did low pierce SSL but close above?
                if candle['low'] < p['price'] and candle['close'] > p['price']:
                    grabs.append({
                        "type": "bullish_grab",
                        "pivot_price": p['price'],
                        "time": df.index[-1],
                        "description": f"Liquidated SSL at {p['price']:.2f} (Bullish SFP)"
                    })
                    
        return grabs

    def detect_liquidity_sweeps(self, df: pd.DataFrame, pivots: Dict[str, List[Dict[str, Any]]], lookback: int = 50) -> List[Dict[str, Any]]:
        """
        Detects powerful Liquidity Sweeps (Displacement through levels).
        Logic: Powerful close BEYOND a level, often starting a trend.
        """
        sweeps = []
        current_idx = len(df) - 1
        candle = df.iloc[-1]

        # Check for Close beyond BSL (Bullish breakout of liquidity)
        for p in pivots['highs']:
             if p['index'] < current_idx - 1 and p['index'] > current_idx - lookback:
                 if candle['close'] > p['price']:
                     sweeps.append({
                         "type": "bsl_sweep",
                         "pivot_price": p['price'],
                         "time": df.index[-1],
                         "description": f"Bullish Sweep of BSL at {p['price']:.2f}"
                     })

        # Check for Close beyond SSL (Bearish breakout of liquidity)
        for p in pivots['lows']:
             if p['index'] < current_idx - 1 and p['index'] > current_idx - lookback:
                 if candle['close'] < p['price']:
                     sweeps.append({
                         "type": "ssl_sweep",
                         "pivot_price": p['price'],
                         "time": df.index[-1],
                         "description": f"Bearish Sweep of SSL at {p['price']:.2f}"
                     })
                     
        return sweeps

def calculate_atr_stop_loss(df: pd.DataFrame, order_block: Dict[str, Any], direction: str, multiplier: float = 1.5) -> float:
    """
    Forced SL Logic using ATR as buffer beyond OB edge.
    If LONG: SL = OB_Bottom - (ATR * Multiplier)
    If SHORT: SL = OB_Top + (ATR * Multiplier)
    """
    from app.indicators import calculate_atr
    atr_series = calculate_atr(df['high'], df['low'], df['close'], window=14)
    last_atr = atr_series.iloc[-2] # Last completed candle ATR
    
    if direction == "BULLISH":
        base_sl = order_block['bottom']
        return base_sl - (last_atr * multiplier)
    else:
        base_sl = order_block['top']
        return base_sl + (last_atr * multiplier)

def calculate_volatility_scaled_position(
    risk_amount: float, 
    entry_price: float, 
    sl_price: float, 
    atr_val: float,
    contract_size: float = 100.0
) -> float:
    """
    Volatility Scaling Logic:
    Integrates the formula from Obsidian to maintain constant risk contribution.
    """
    price_risk = abs(entry_price - sl_price)
    if price_risk == 0: return 0.0
    
    # Standard Position Sizing
    size = risk_amount / (price_risk * contract_size)
    
    # Potential Volatility Scaling factor (to be refined based on SPC)
    # If ATR is higher than average, size is reduced further.
    return round(size, 2)
