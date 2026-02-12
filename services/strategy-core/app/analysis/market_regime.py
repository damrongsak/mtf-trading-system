import pandas as pd
import numpy as np
from typing import Dict, Any, TypedDict, Optional
from enum import Enum
from app.indicators.trend import detect_trend_structure
from app.indicators.smc import detect_liquidity_sweeps

class MarketRegime(str, Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    UNSTABLE = "UNSTABLE"

class MarketContext(TypedDict):
    regime: MarketRegime
    regime_score: float  # ADX value
    is_fakeout: bool
    fakeout_type: Optional[str] # 'SFP_HIGH', 'SFP_LOW'
    recommended_risk: float
    risk_multiplier: float
    meta: Dict[str, Any]

def detect_regime(df: pd.DataFrame, adx_threshold: int = 25) -> MarketRegime:
    """
    Detects the current market regime using ADX and Price Action.
    
    Logic:
    - ADX > 25: TRENDING
    - ADX < 20: RANGING
    - Else: UNSTABLE / TRANSITION
    """
    if df.empty:
        return MarketRegime.UNSTABLE

    # Use existing vectorbt optimized indicator
    structure_df = detect_trend_structure(df['high'], df['low'], df['close'])
    
    last_row = structure_df.iloc[-1]
    adx = last_row['adx']
    
    # Determine Direction for Trending
    # Simple check: Close > EMA50 for UP, < EMA50 for DOWN (calculated here for simplicity or passed in)
    # For now, we return generic TRENDING, or infer from price location relative to SMA20/50?
    
    # Let's derive direction from the last few candles if ADX is high
    close = df['close']
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    last_close = close.iloc[-1]

    if adx > adx_threshold:
        if last_close > ema50:
            return MarketRegime.TRENDING_UP
        else:
            return MarketRegime.TRENDING_DOWN
    elif adx < 20:
        return MarketRegime.RANGING
    
    return MarketRegime.UNSTABLE

def detect_fakeout_alignment(df: pd.DataFrame, bias: str) -> Optional[str]:
    """
    Checks if the current price action aligns with a 'Fade' or 'Trap' move.
    
    Returns:
    - 'SFP_HIGH': Recent liquidity sweep of highs (Bearish SFP)
    - 'SFP_LOW': Recent liquidity sweep of lows (Bullish SFP)
    - None: No fakeout detected
    """
    if df.empty:
        return None
        
    sweeps = detect_liquidity_sweeps(df)
    if not sweeps:
        return None
        
    # Look for very recent sweeps (last 3-5 candles)
    last_sweep = sweeps[-1]
    
    # Ensure it's recent (index within last 5 bars)
    if last_sweep['index'] < len(df) - 5:
        return None
        
    if last_sweep['type'] == 'bearish_sweep' and bias == 'BEARISH':
        return "SFP_HIGH"
    elif last_sweep['type'] == 'bullish_sweep' and bias == 'BULLISH':
        return "SFP_LOW"
        
    return None

def calculate_dynamic_risk(regime: MarketRegime, is_fakeout: bool) -> float:
    """
    Returns the Risk Multiplier based on Probabilistic Context.
    
    Logic:
    1. Trend Following (Trending + No Fakeout): Normal Risk (1.0x)
    2. Counter Trend (Ranging + SFP): High Prob Setup (1.2x)
    3. Counter Trend (Trending + SFP): Fade Attempt (0.5x)
    4. Unstable: Low Risk (0.25x)
    """
    multiplier = 1.0
    
    if regime == MarketRegime.UNSTABLE:
        multiplier = 0.5
        
    elif regime == MarketRegime.RANGING:
        if is_fakeout:
            # Range Bound + Fade Sweep = High Prob
            multiplier = 1.2
        else:
            # Random chop
            multiplier = 0.5
            
    elif regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
        if is_fakeout:
             # Fading a clear trend? Risky.
             multiplier = 0.5
        else:
            # Trend following
            multiplier = 1.0
            
    return multiplier

def get_market_context(df: pd.DataFrame, bias_direction: str = "NEUTRAL") -> MarketContext:
    """
    Returns a unified context object for the Strategy Logic and AI Analyst.
    """
    regime = detect_regime(df)
    fakeout_type = detect_fakeout_alignment(df, bias_direction)
    is_fakeout = fakeout_type is not None
    
    # Get numeric score (ADX)
    structure_df = detect_trend_structure(df['high'], df['low'], df['close'])
    adx_score = float(structure_df['adx'].iloc[-1]) if not structure_df.empty else 0.0
    
    risk_mult = calculate_dynamic_risk(regime, is_fakeout)
    
    return {
        "regime": regime,
        "regime_score": adx_score,
        "is_fakeout": is_fakeout,
        "fakeout_type": fakeout_type,
        "recommended_risk": risk_mult, # Now returns multiplier (kept key name for compat, or semantic change?)
        # Let's add a clear key for AI
        "risk_multiplier": risk_mult,
        "meta": {
            "bias_input": bias_direction,
            "can_trade_trend": "TRENDING" in regime,
            "can_trade_reversion": regime == MarketRegime.RANGING or is_fakeout
        }
    }
