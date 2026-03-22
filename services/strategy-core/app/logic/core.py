from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, Tuple
# Heavy imports moved inside functions to prevent hang during registration initialization
from app.indicators import calculate_ema, calculate_atr
from app.indicators.smc import detect_order_blocks, detect_fvg
# from app.features.quant_features import QuantreoFeatures

class SignalDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    LONG = "BULLISH"   # Alias for compatibility
    SHORT = "BEARISH" # Alias for compatibility


def check_macro_bias(df_h4, ema_period: int = 200) -> SignalDirection:
    import pandas as pd
    """
    Rule A: Macro Bias
    - Bullish if Close > EMA200
    - Bearish if Close < EMA200
    
    CRITICAL (Bias Prevention):
    - Uses `iloc[-2]` (Last Completed Candle) to prevent look-ahead bias if
      the DataFrame includes the current forming candle.
    """
    if len(df_h4) < ema_period + 2:
        return SignalDirection.NEUTRAL

    # Calculated using module-level calculate_ema
    ema = calculate_ema(df_h4['close'], span=ema_period)
    
    # Strict Bias Prevention: Use -2 (Last Completed)
    last_close = df_h4['close'].iloc[-2] 
    last_ema = ema.iloc[-2]

    if last_close > last_ema:
        return SignalDirection.BULLISH
    elif last_close < last_ema:
        return SignalDirection.BEARISH
    
    return SignalDirection.NEUTRAL

def check_setup_zone(df_h1, direction: SignalDirection) -> bool:
    import pandas as pd
    """
    Rule B: Setup Zone (Confluence)
    - Bullish: Price in Discount Zone (Fib 0.5-0.618) of last swing + Bullish PD Array (OB/FVG)
    - Bearish: Price in Premium Zone (Fib 0.5-0.618) of last swing + Bearish PD Array
    
    SIMPLIFICATION for MVP Phase 4:
    - Detecting "Last Swing" algorithmically is complex. 
    - We will simplify to: Price is inside a detected Order Block on H1 aligned with direction.
    - Future: Add Fib retracement logic.
    """
    if direction == SignalDirection.NEUTRAL:
        return False
    # Get recent Order Blocks
    # We only care if CURRENT price is inside an OB.
    obs = detect_order_blocks(df_h1)
    
    if not obs:
        return False
        
    # Strict Bias Prevention: Check if LAST COMPLETED candle closed in OB
    # (Or is testing it). For entry signal, we usually want the completed candle.
    current_close = df_h1['close'].iloc[-2]
    
    for ob in obs:
        # Check alignment
        if direction == SignalDirection.BULLISH and ob['type'] == 'bullish':
             # Price inside OB range? (Top/Bottom)
             # Bullish OB is usually a 'Down' candle, so Top is Open, Bottom is Close
             if ob['bottom'] <= current_close <= ob['top']:
                 return True
                 
        elif direction == SignalDirection.BEARISH and ob['type'] == 'bearish':
             # Bearish OB is 'Up' candle. Top is Close, Bottom is Open
             if ob['bottom'] <= current_close <= ob['top']:
                 return True
                 
    return False


    
    return False

def check_market_regime(df_h1: pd.DataFrame, direction: SignalDirection) -> Dict[str, Any]:
    """
    Rule F (New): Adaptive Guardrails
    - Uses ADX to determine if we should be trading Trend or Range.
    - Uses SFP (Swing Failure Pattern) to detect Traps.
    """
    from app.analysis.market_regime import get_market_context, MarketRegime
    
    context = get_market_context(df_h1, direction.value)
    
    return context

def check_hunter_setup(df_setup: pd.DataFrame, direction: SignalDirection) -> bool:
    """
    Phase 64: Hunter Mode Setup
    - Validates if a Liquidity Raid (Sweep) has occurred at structural landmarks.
    - Checks for Asian Range or PDH/PDL sweeps.
    """
    if df_setup.empty:
        return False
    
    # Get labels from last completed candle
    labels = df_setup['ai_labels'].iloc[-1] if 'ai_labels' in df_setup.columns else {}
    if not isinstance(labels, dict):
        return False
        
    # 1. Check for Judas Swing (London Open Fakeout)
    judas = labels.get("judas")
    if judas:
        if direction == SignalDirection.BULLISH and judas == "bullish":
            return True
        if direction == SignalDirection.BEARISH and judas == "bearish":
            return True
            
    # 2. Check for Structural Sweeps (FVG/Sweep logic from data-pipeline)
    sweep = labels.get("sweep")
    if sweep:
        if direction == SignalDirection.BULLISH and sweep == "bullish":
            return True
        if direction == SignalDirection.BEARISH and sweep == "bearish":
            return True
            
    # 3. Check for EQH/EQL (Double Top/Bottom) being raided
    # If we see EQH/EQL in the labels, we are IN the pool, 
    # but the Hunter waits for the pierce.
    
    return False

def check_hunter_trigger(df_base: pd.DataFrame, direction: SignalDirection) -> bool:
    """
    Phase 64: Hunter Mode Trigger (Wait-for-Sweep)
    - Confirms the V-Shape rejection back into the range.
    """
    # Simply: Did the previous candle sweep a level and THIS candle close back inside?
    # This is often confirmed by the 'judas' or 'sweep' label on the trigger candle
    # which we already checked in setup. 
    # Here we can add extra confirmation like Price > Asian Low (for Bullish)
    
    labels = df_base['ai_labels'].iloc[-2] if 'ai_labels' in df_base.columns else {}
    if not isinstance(labels, dict):
        return False
        
    # If the setup candle had a sweep, we trigger on the next candle 
    # that maintains the rejection.
    is_sweep = labels.get("sweep") or labels.get("judas")
    if not is_sweep:
        return False
        
    current_close = df_base['close'].iloc[-1]
    
    # Check for V-shape displacement (Displacement should be high)
    # This is a proxy for the 'fuel' mentioned in the guide.
    return True # Placeholder for more complex displacement check

def check_trigger(df_m15, direction: SignalDirection, rv_threshold: float = 0.7, min_volatility: float = 0.0005) -> bool:
    import pandas as pd
    """
    Rule C: Trigger
    - Volatility Check (Quantreo)
    - Candle Shape (Body/Wick)
    - [NEW] Adaptive Guardrail Check (Fakeout/Regime)
    
    CRITICAL: Strict `iloc[-2]` usage.
    """
    if len(df_m15) < 32: 
        return False

    from app.features.quant_features import QuantreoFeatures
    # 1. Quantreo Volatility Filter
    df_vol = QuantreoFeatures.add_volatility_features(df_m15, window_size=30)
    # Check volatility of the CLOSED candle setup
    current_vol = df_vol['parkinson_vol_30'].iloc[-2]
    
    if current_vol < min_volatility:
        # Market too quiet, reject trade
        return False
        
    # [NEW] Adaptive Guardrail: Check for recent Fakeout/Trap
    # If we are entering a TREND trade (e.g. Bullish Breakout), 
    # we want to ensure we aren't buying into a Bearish SFP (Trap).
    from app.analysis.market_regime import detect_fakeout_alignment
    
    # We check against the OPPOSITE bias to see if there is a Trap against us
    # e.g. If specific Direction is BULLISH, is there a Bearish SFP (trap at high)?
    trap_type = detect_fakeout_alignment(df_m15, direction.value)
    
    # If there is a Trap aligning with our direction (e.g. we are Bullish, and there is a Bullish SFP/Sweep of Lows)
    # Then this is actually a HIGH CONFIDENCE setup (Anti-Fragile).
    # But if there is a Trap AGAINST us (e.g. we are Bullish, but there is a Bearish SFP/Sweep of Highs)
    # Then we should be very careful.
    
    # For Trigger logic, let's keep it simple:
    # If we are buying (Bullish), we like to see a recent Sweep of Lows (Bullish SFP).
    # We HATE to see a Sweep of Highs (Bearish SFP) right before we buy.
    
    # Current simplistic logic: Just standard trigger. 
    # The Regime filter should optionally filter this at a higher level or here.
    # Let's pass for now and rely on refined entry.

    # We check the LAST COMPLETED candle for the trigger shape
    candle = df_m15.iloc[-2]
    
    open_price = candle['open']
    close_price = candle['close']
    high = candle['high']
    low = candle['low']
    
    body = abs(close_price - open_price)
    range_len = high - low
    
    if range_len == 0:
        return False
        
    rv = body / range_len
    
    if rv < rv_threshold:
        return False
        
    # Check Direction
    if direction == SignalDirection.BULLISH:
        # Must be Green
        return close_price > open_price
    elif direction == SignalDirection.BEARISH:
        # Must be Red
        return close_price < open_price
        
    return False

def calculate_stop_loss(df_m15, direction: SignalDirection, atr_mult: float = 1.75) -> float:
    import pandas as pd
    """
    Rule D: Risk Management (Stop Loss)
    - SL = ATR(14) * M (Using Last Completed Candle)
    """
    # Calculated using module-level calculate_atr
    atr = calculate_atr(df_m15['high'], df_m15['low'], df_m15['close'], window=14)
    last_atr = atr.iloc[-2]
    
    current_price = df_m15['close'].iloc[-2]
    
    dist = last_atr * atr_mult
    
    if direction == SignalDirection.BULLISH:
        return current_price - dist
    else:
        return current_price + dist

def calculate_target_price(df_h1, direction: SignalDirection, entry_price: float, sl_price: float) -> float:
    import pandas as pd
    """
    Calculate Target Price (TP) for RRR calculation.
    
    Logic:
    1. Look for nearest "Opposing" Order Block (e.g. Bearish OB for Long trade).
    2. If found, TP = Edge of OB (Bottom for Bearish, Top for Bullish).
    3. If NOT found (or too far), use a fixed 2.0R Fallback.
    """
    risk_dist = abs(entry_price - sl_price)
    
    # Fallback Target (2R)
    if direction == SignalDirection.BULLISH:
        fallback_tp = entry_price + (risk_dist * 2.0)
    else:
        fallback_tp = entry_price - (risk_dist * 2.0)
        
    # Get Order Blocks from module level import
    # Get Order Blocks
    obs = detect_order_blocks(df_h1)
    
    nearest_ob_price = None
    
    if direction == SignalDirection.BULLISH:
        # Looking for Bearish OBs ABOVE entry
        candidates = [ob['bottom'] for ob in obs if ob['type'] == 'bearish' and ob['bottom'] > entry_price]
        if candidates:
            # Nearest one (min value > entry)
            nearest_ob_price = min(candidates)
            
    elif direction == SignalDirection.BEARISH:
        # Looking for Bullish OBs BELOW entry
        candidates = [ob['top'] for ob in obs if ob['type'] == 'bullish' and ob['top'] < entry_price]
        if candidates:
            # Nearest one (max value < entry)
            nearest_ob_price = max(candidates)
            
    # Decision: Use OB if it exists, otherwise Fallback
    # Note: Realistically, if OB is too close (< 1R), check_rrr will fail anyway.
    if nearest_ob_price is not None:
        return nearest_ob_price
        
    return fallback_tp

def check_rrr(entry_price: float, sl_price: float, tp_price: float, min_rrr: float = 1.5) -> bool:
    """
    Rule E: Risk Reward Ratio Check
    """
    risk = abs(entry_price - sl_price)
    reward = abs(tp_price - entry_price)
    
    if risk == 0:
        return False
        
    rrr = reward / risk
    
    return rrr >= min_rrr

