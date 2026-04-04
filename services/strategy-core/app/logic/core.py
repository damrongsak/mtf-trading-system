from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, Tuple
# Heavy imports moved inside functions to prevent hang during registration initialization
from app.indicators import calculate_ema, calculate_atr
from app.indicators.smc import detect_order_blocks, detect_fvg, calculate_displacement_velocity
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

def detect_choch(df: pd.DataFrame, direction: SignalDirection) -> Tuple[bool, str]:
    """
    Detects Change of Character (CHoCH) on the trigger timeframe.
    Bullish CHoCH: Low[i] < Recent Low (Sweep) followed by Close[j] > Last LH (Shift).
    """
    if len(df) < 20:
        return False, "Insufficient data for CHoCH"
        
    from app.indicators.smc import detect_structure
    structure = detect_structure(df, window=3)
    
    # 1. Look for the most recent high/low pivots
    pivots = structure.get("pivots", [])
    if len(pivots) < 2:
        return False, "No established structure for CHoCH"
        
    last_close = df['close'].iloc[-1]
    
    if direction == SignalDirection.BULLISH:
        # Bullish CHoCH: Price breaks above the last Lower High (LH)
        lh_pivots = [p for p in pivots if p["type"] == "high"]
        if not lh_pivots:
             return False, "No LH found to break"
        
        last_lh = lh_pivots[-1]
        if last_close > last_lh["price"]:
             return True, f"Bullish CHoCH: Price broke LH at {last_lh['price']:.2f}"
    
    elif direction == SignalDirection.BEARISH:
        # Bearish CHoCH: Price breaks below the last Higher Low (HL)
        hl_pivots = [p for p in pivots if p["type"] == "low"]
        if not hl_pivots:
             return False, "No HL found to break"
             
        last_hl = hl_pivots[-1]
        if last_close < last_hl["price"]:
             return True, f"Bearish CHoCH: Price broke HL at {last_hl['price']:.2f}"
             
    return False, "Structure remains intact"

def detect_bos_recent(df: pd.DataFrame, direction: SignalDirection, lookback: int = 15) -> bool:
    """
    Checks if a Break of Structure (BOS) occurred within the recent lookback window.
    BOS is a trend-continuation break (High[i] > HH or Low[i] < LL).
    """
    from app.indicators.smc import detect_structure
    structure = detect_structure(df, window=5)
    
    events = structure.get("events", [])
    if not events:
        return False
        
    recent_events = [e for e in events if e["index"] >= len(df) - lookback]
    
    for event in recent_events:
        if direction == SignalDirection.BULLISH and event["type"] == "bos_bullish":
            return True
        if direction == SignalDirection.BEARISH and event["type"] == "bos_bearish":
            return True
            
    return False

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


def calculate_confluence_score(
    df_macro: pd.DataFrame, 
    df_poi: pd.DataFrame, 
    df_trigger: pd.DataFrame, 
    direction: SignalDirection
) -> Dict[str, Any]:
    """
    Institutional 1-6 Point Confluence Scoring (SMC v2.4)
    Supports Flexible Trigger (M1, M5, or M15).
    """
    import pandas as pd
    checklist = {}
    metrics = {}
    score = 0

    last_close = float(df_trigger['close'].iloc[-1])

    # 1. Trend (H4)
    bias = check_macro_bias(df_macro)
    trend_pass = bias == direction
    
    # Capture Macro EMA for metrics
    from app.indicators.trend import calculate_ema
    ema_h4 = calculate_ema(df_macro['close'], span=200)
    last_ema_h4 = float(ema_h4.iloc[-1]) if not ema_h4.empty else 0.0
    
    checklist["trend"] = {
        "status": trend_pass,
        "value": bias.value,
        "comment": f"Macro Bias is {bias.value} (Price {last_close:.2f} vs H4 EMA {last_ema_h4:.2f}). Target: {direction.value}"
    }
    metrics["h4_ema_200"] = str(round(last_ema_h4, 2))
    if trend_pass: score += 1

    # 2. POI (H1)
    poi_pass = check_setup_zone(df_poi, direction)
    
    # Find nearest POI for comment
    from app.indicators.smc import detect_order_blocks
    obs_h1 = detect_order_blocks(df_poi)
    nearest_ob_price = "N/A"
    if obs_h1:
        active_obs = [ob for ob in obs_h1 if not ob.get("mitigated") and ob['type'] == ('bullish' if direction == SignalDirection.BULLISH else 'bearish')]
        if active_obs:
            nearest_ob = active_obs[-1]
            nearest_ob_price = f"{nearest_ob['top']:.2f}" if direction == SignalDirection.BULLISH else f"{nearest_ob['bottom']:.2f}"

    checklist["poi"] = {
        "status": poi_pass,
        "value": "Inside OB/FVG" if poi_pass else "No POI",
        "comment": f"Price testing POI zone at {nearest_ob_price}" if poi_pass else f"Price ({last_close:.2f}) has not reached POI zone ({nearest_ob_price})"
    }
    metrics["poi_reference_price"] = nearest_ob_price
    if poi_pass: score += 1

    # 3. Trigger (Flexible: M1/M5/M15)
    choch_pass, choch_msg = detect_choch(df_trigger, direction)
    checklist["trigger"] = {
        "status": choch_pass,
        "value": "CHoCH Confirmed" if choch_pass else "Wait for CHoCH",
        "comment": f"{choch_msg} (Last Price: {last_close:.2f})"
    }
    if choch_pass: score += 1

    # 4. Displacement
    v_d = calculate_displacement_velocity(df_trigger)
    last_v = float(v_d.iloc[-1]) if not v_d.empty else 0.0
    disp_pass = last_v > 1.3 # Expansion threshold
    checklist["displacement"] = {
        "status": disp_pass,
        "value": f"{last_v:.2f}",
        "comment": f"Expansion velocity {last_v:.2f} confirmed (>1.3 threshold)" if disp_pass else f"Low momentum entry (Velocity {last_v:.2f} < 1.3)"
    }
    metrics["displacement_velocity"] = str(round(last_v, 2))
    if disp_pass: score += 1

    # 5. Volatility
    from app.indicators.volatility import calculate_atr
    atr = calculate_atr(df_poi['high'], df_poi['low'], df_poi['close'])
    current_atr = float(atr.iloc[-1]) if not atr.empty else 0.0
    avg_atr = float(atr.rolling(window=50).mean().iloc[-1]) if len(atr) > 50 else current_atr
    vol_pass = current_atr >= (avg_atr * 0.7) # Not too quiet
    checklist["volatility"] = {
        "status": vol_pass,
        "value": f"{current_atr:.5f}",
        "comment": f"ATR {current_atr:.5f} >= {avg_atr*0.7:.5f} (70% of Avg)" if vol_pass else f"Thin liquidity: ATR {current_atr:.5f} < {avg_atr*0.7:.5f}"
    }
    metrics["current_atr"] = str(round(current_atr, 5))
    metrics["avg_atr_50"] = str(round(avg_atr, 5))
    if vol_pass: score += 1

    # 6. Risk/Reward
    sl = calculate_stop_loss(df_trigger, direction)
    entry = df_trigger['close'].iloc[-1]
    tp = calculate_target_price(df_poi, direction, entry, sl)
    
    rrr = 0.0
    if abs(entry - sl) > 0:
        rrr = abs(tp - entry) / abs(entry - sl)
        
    rrr_pass = check_rrr(entry, sl, tp, min_rrr=1.5)
    checklist["risk_reward"] = {
        "status": rrr_pass,
        "value": f"1:{rrr:.2f}",
        "comment": f"Attractive RRR 1:{rrr:.2f} (Target TP: {tp:.2f})" if rrr_pass else f"Poor RRR 1:{rrr:.2f} (Target TP: {tp:.2f}, SL: {sl:.2f})"
    }
    metrics["rrr_ratio"] = str(round(rrr, 2))
    if rrr_pass: score += 1

    # Summary
    summary = f"Institutional Confluence: {score}/6. "
    if score >= 5:
        summary += "High-conviction SMC setup."
    elif score >= 3:
        summary += "Intermediate setup, consider lower leverage."
    else:
        summary += "Failed institutional filters."

    return {
        "score": score,
        "checklist": checklist,
        "metrics": metrics,
        "summary": summary,
        "bias": direction.value,
        "visuals": {
             "trigger_level": float(entry),
             "stop_loss": float(sl),
             "take_profit": float(tp)
        }
    }

def detect_case_b_mitigation(df_poi: pd.DataFrame, direction: SignalDirection) -> Tuple[bool, str]:
    """
    Case B Detection: Mitigation AFTER BOS.
    - Check for BOS in the last 15 candles.
    - Check if price is currently tapping an OB.
    """
    has_bos = detect_bos_recent(df_poi, direction, lookback=15)
    if not has_bos:
        return False, "Case B Rejected: No recent BOS before mitigation tap"
        
    obs = detect_order_blocks(df_poi)
    if not obs:
        return False, "No Order Blocks found on POI timeframe"
        
    current_close = df_poi['close'].iloc[-1]
    
    for ob in reversed(obs):
        if direction == SignalDirection.BULLISH and ob['type'] == 'bullish':
            if ob['bottom'] <= current_close <= ob['top']:
                return True, f"Case B Confirmed: Bullish Mitigation tap after BOS"
        elif direction == SignalDirection.BEARISH and ob['type'] == 'bearish':
            if ob['bottom'] <= current_close <= ob['top']:
                return True, f"Case B Confirmed: Bearish Mitigation tap after BOS"
                
    return False, "Case B Rejected: No active mitigation tap"

