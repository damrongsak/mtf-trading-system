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
    EXPANSION_UP = "EXPANSION_UP"
    EXPANSION_DOWN = "EXPANSION_DOWN"

class MarketContext(TypedDict):
    regime: MarketRegime
    regime_score: float  # ADX value
    adx_slope: float
    plus_di: float
    minus_di: float
    is_fakeout: bool
    is_expansion: bool
    fakeout_type: Optional[str] # 'SFP_HIGH', 'SFP_LOW'
    recommended_risk: float
    risk_multiplier: float
    meta: Dict[str, Any]

def detect_expansion(df: pd.DataFrame) -> bool:
    """
    Detects if the market is in a hyperbolic expansion phase (V_d > 3 sigma).
    Uses displacement velocity as a proxy.
    """
    if len(df) < 30:
        return False
    
    # Logic similar to smc.py calculate_displacement_velocity
    body = (df['close'] - df['open']).abs()
    v_d = body / body.rolling(window=20).mean()
    v_d_rolling_mean = v_d.rolling(window=20).mean()
    v_d_rolling_std = v_d.rolling(window=20).std()
    
    is_exp = v_d.iloc[-1] > (v_d_rolling_mean.iloc[-1] + 3 * v_d_rolling_std.iloc[-1])
    return bool(is_exp)

def detect_regime(df: pd.DataFrame, adx_threshold: int = 25) -> MarketRegime:
    """
    Detects the current market regime using ADX and Price Action.
    Enhanced with Expansion detection.
    """
    if df.empty:
        return MarketRegime.UNSTABLE

    is_exp = detect_expansion(df)
    
    # Use existing vectorbt optimized indicator
    structure_df = detect_trend_structure(df['high'], df['low'], df['close'])
    
    last_row = structure_df.iloc[-1]
    adx = last_row['adx']
    
    close = df['close']
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    last_close = close.iloc[-1]

    if is_exp:
        return MarketRegime.EXPANSION_UP if last_close > ema50 else MarketRegime.EXPANSION_DOWN

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
    """
    if df.empty:
        return None
        
    sweeps = detect_liquidity_sweeps(df)
    if not sweeps:
        return None
        
    last_sweep = sweeps[-1]
    
    if last_sweep['index'] < len(df) - 5:
        return None
        
    # Guardrail: Rejections from Hyperbolic Expansion are excluded in smc.py
    # But we double check here to be sure.
    if last_sweep.get('meta', {}).get('is_hyperbolic_rejection', False):
        return None

    if last_sweep['type'] == 'bearish_sweep' and bias == 'BEARISH':
        return "SFP_HIGH"
    elif last_sweep['type'] == 'bullish_sweep' and bias == 'BULLISH':
        return "SFP_LOW"
    
    return None

def calculate_dynamic_risk(regime: MarketRegime, is_fakeout: bool, base_risk: float = 1.0) -> float:
    """
    Returns the Risk Multiplier based on Probabilistic Context.
    Enhanced for Expansion phases.
    """
    multiplier = 1.0
    
    if regime in (MarketRegime.EXPANSION_UP, MarketRegime.EXPANSION_DOWN):
        # Hyperbolic expansion is toxic for reversals. Kill risk for fades.
        multiplier = 0.1 if is_fakeout else 0.75 # Lower risk even for trend following in parabolic
        
    elif regime == MarketRegime.UNSTABLE:
        multiplier = 0.5
        
    elif regime == MarketRegime.RANGING:
        if is_fakeout:
            multiplier = 1.2
        else:
            multiplier = 0.5
            
    elif regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
        if is_fakeout:
             multiplier = 0.5
        else:
            multiplier = 1.0
            
    return multiplier * base_risk

def get_market_context(df: pd.DataFrame, bias_direction: str = "NEUTRAL") -> MarketContext:
    """
    Returns a unified context object for the Strategy Logic and AI Analyst.
    """
    regime = detect_regime(df)
    is_expansion = regime in (MarketRegime.EXPANSION_UP, MarketRegime.EXPANSION_DOWN)
    
    fakeout_type = detect_fakeout_alignment(df, bias_direction)
    is_fakeout = fakeout_type is not None
    
    # Get numeric score (ADX) and components
    adx_df = detect_trend_structure(df['high'], df['low'], df['close'])
    if adx_df.empty:
        adx_score = 0.0
        adx_slope = 0.0
        plus_di = 0.0
        minus_di = 0.0
    else:
        from app.indicators.trend import calculate_adx
        full_adx = calculate_adx(df['high'], df['low'], df['close'])
        
        last_row = full_adx.iloc[-1]
        adx_score = float(last_row['adx'])
        plus_di = float(last_row['dmp'])
        minus_di = float(last_row['dmn'])
        
        if len(full_adx) >= 3:
            adx_series = full_adx['adx']
            adx_slope = float(adx_series.iloc[-1] - adx_series.iloc[-3])
        else:
            adx_slope = 0.0
    
    risk_mult = calculate_dynamic_risk(regime, is_fakeout)
    
    return {
        "regime": regime,
        "regime_score": adx_score,
        "adx_slope": adx_slope,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "is_fakeout": is_fakeout,
        "is_expansion": is_expansion,
        "fakeout_type": fakeout_type,
        "recommended_risk": risk_mult,
        "risk_multiplier": risk_mult,
        "meta": {
            "bias_input": bias_direction,
            "can_trade_trend": "TRENDING" in regime or "EXPANSION" in regime,
            "can_trade_reversion": (regime == MarketRegime.RANGING or is_fakeout) and not is_expansion
        }
    }
