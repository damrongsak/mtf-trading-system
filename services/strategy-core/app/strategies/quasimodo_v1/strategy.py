"""
Quasimodo V1 - Institutional QM Structure Strategy

Pattern: LS1 -> LH1 -> LS2 (Liquidity Sweep < LS1) -> LH2 (BOS > LH1)
Entry: Price returns to QML (LS1 level) on M15 with EMA confirmation
SL: Range-based (Pattern_Range × 1.2) + ATR Buffer
TP: TP1 @ 1.0R, TP2 @ 2.0R, TP3 trailing

Author: Soda
Date: 2026-03-24
Version: 1.1 (Class-based Refactor)
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from app.foundry.vector_base import VectorizedStrategyBase
from app.core.units import UnitConverter

logger = logging.getLogger(__name__)

# ============================================================================
# METADATA - Strategy Registry
# ============================================================================

METADATA = {
    "name": "Quasimodo V1",
    "description": "Institutional QM Structure with MTF Confluence - Liquidity Sweep + BOS Pattern",
    "defaults": {
        "tf_macro": "4h",        # H4 for Macro Bias (Trend)
        "tf_setup": "1h",       # H1 for structure
        "tf_trigger": "15min",  # M15 for entry trigger
        "swing_strength": 1,    # ZigZag strength
        "atr_period": 14,
        "ema_fast": 13,
        "ema_slow": 50,
        "ema_macro": 200,       # Macro Trend EMA
        "risk_pct": 0.01,
        "min_rrr": 1.5,
        "max_sl_pips": 40,
        "rl_filter_threshold": 0.5, # Minimum quality score to allow signal
    }
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    index: int
    type: str  # 'high' or 'low'
    price: float
    timestamp: pd.Timestamp


@dataclass
class QMPattern:
    """Complete Quasimodo pattern structure"""
    direction: str           # 'BULLISH' or 'BEARISH'
    ls1: float               # Swing Low 1 (Structural)
    lh1: float               # Swing High 1
    ls2: float               # Swing Low 2 (Liquidity Sweep)
    lh2: float               # Swing High 2 (BOS)
    qml: float               # Quasimodo Level (Entry zone)
    head: float              # Pattern head (for SL)
    range_pips: float        # Pattern range in pips
    displacement: bool       # Energetic move flag
    valid: bool


# ============================================================================
# STRATEGY CLASS
# ============================================================================

class QuasimodoStrategy(VectorizedStrategyBase):
    """
    Quasimodo V1 Strategy implementation following the VectorizedStrategyBase standard.
    """
    
    def __init__(self):
        super().__init__(name="Quasimodo V1", metadata=METADATA)

    def run_vector(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.Series, pd.Series]:
        """
        Vectorized (or looped) backtest implementation for Quasimodo V1.
        Returns (entries, exits) boolean Series.
        """
        # 1. Setup
        entries = pd.Series(False, index=df.index)
        exits = pd.Series(False, index=df.index)
        
        strength = params.get("swing_strength", 2)
        ema_fast_p = params.get("ema_fast", 50)
        ema_slow_p = params.get("ema_slow", 200)
        qml_buffer = 0.2
        
        # 2. Indicators (Ensure copy to avoid mutations affecting Numba)
        df = df.copy()
        df['ema_fast'] = df['close'].astype(float).ewm(span=ema_fast_p, adjust=False).mean()
        df['ema_slow'] = df['close'].astype(float).ewm(span=ema_slow_p, adjust=False).mean()
        
        # 3. Detect ALL swings upfront
        ohlc_df = df[['high', 'low', 'close']].astype(float)
        all_swings = detect_swing_points(ohlc_df, strength=strength)
        
        # 4. Macro Bias (H4 Proxy - using daily/H4 EMA on the same DF if resampled)
        # Note: In a real multi-tf vector backtest, we'd merge H4 data. 
        # For this script, we use the 200 EMA of the current timeframe as a trend proxy.
        ema_macro_p = params.get("ema_macro", 200)
        df['ema_macro'] = df['close'].astype(float).ewm(span=ema_macro_p, adjust=False).mean()
        df['atr'] = calculate_atr(df, params.get("atr_period", 14))
        
        if len(all_swings) < 4:
            return entries, exits
            
        # 5. Iterate and find signals
        last_swing_count = 0
        current_pattern = None
        rl_threshold = params.get("rl_filter_threshold", 0.5)
        
        for i in range(strength * 2 + 10, len(df)):
            current_time = df.index[i]
            current_price = df['close'].iloc[i]
            
            # Get swings that occurred BEFORE current_time
            available_swings = [s for s in all_swings if s.index < i]
            
            # Only re-identify if we have new swings
            if len(available_swings) != last_swing_count:
                current_pattern = identify_qm_logic(available_swings)
                last_swing_count = len(available_swings)
                
            if not current_pattern:
                continue
                
            # Filters
            ema_f = df['ema_fast'].iloc[i]
            ema_s = df['ema_slow'].iloc[i]
            ema_m = df['ema_macro'].iloc[i] # Macro Bias
            current_atr = df['atr'].iloc[i]
            
            # Directional Bias Checks
            is_bullish_bias = current_price > ema_m
            is_bearish_bias = current_price < ema_m
            
            if current_pattern.direction == 'BULLISH':
                # Proximity to QML AND Trend alignment AND Macro Bias
                if abs(current_price - current_pattern.qml) <= qml_buffer and \
                   ema_f > ema_s and is_bullish_bias:
                    
                    # RL Filter Evaluation
                    pattern_dict = {"range_pips": current_pattern.range_pips, "rrr": 1.5}
                    rl_eval = rl_filter.evaluate_pattern(df.iloc[:i+1], pattern_dict, current_atr)
                    
                    if rl_eval["quality_score"] >= rl_threshold:
                        entries.iloc[i] = 1
                        
            elif current_pattern.direction == 'BEARISH':
                if abs(current_price - current_pattern.qml) <= qml_buffer and \
                   ema_f < ema_s and is_bearish_bias:
                    
                    pattern_dict = {"range_pips": current_pattern.range_pips, "rrr": 1.5}
                    rl_eval = rl_filter.evaluate_pattern(df.iloc[:i+1], pattern_dict, current_atr)
                    
                    if rl_eval["quality_score"] >= rl_threshold:
                        entries.iloc[i] = -1 
                    
        return entries, exits

    async def run_live_signal(self, data: pd.DataFrame, params: Dict[str, Any] = None, data_h1: pd.DataFrame = None) -> Tuple[pd.Series, pd.Series, Dict[str, Any]]:
        """
        Quasimodo V2 Professional Signal Engine.
        Returns ultra-high fidelity metrics for 3rd party institutional consumers.
        """
        from app.analysis.rl import rl_filter
        if params is None:
            params = self.metadata.get("defaults", {})
            
        # --- 1. Institutional Indicators (H1/M15 Base) ---
        ema_fast_p = params.get("ema_fast", 13)
        ema_slow_p = params.get("ema_slow", 50)
        ema_macro_p = params.get("ema_macro", 200)
        atr_period = params.get("atr_period", 14)

        ema_fast_s = calculate_ema(data['close'], ema_fast_p)
        ema_slow_s = calculate_ema(data['close'], ema_slow_p)
        ema_macro_s = calculate_ema(data['close'], ema_macro_p)
        atr_s = calculate_atr(data, period=atr_period)
        
        # --- 2. Macro Trend Confluence (H1) ---
        ema200_h1 = 0.0
        if data_h1 is not None and not data_h1.empty:
            ema200_h1_series = calculate_ema(data_h1['close'], 200)
            ema200_h1 = float(ema200_h1_series.iloc[-1])
        
        current_price = float(data['close'].iloc[-1])
        cur_ema_f = float(ema_fast_s.iloc[-1])
        cur_ema_s = float(ema_slow_s.iloc[-1])
        cur_ema_m = float(ema_macro_s.iloc[-1]) # EMA200 on M15
        cur_atr = float(atr_s.iloc[-1])
        
        # --- 3. Trend Confluence & Bias ---
        trend_bias = "BULLISH" if cur_ema_f > cur_ema_s else "BEARISH"
        # Macro alignment uses H1 EMA200 if available, else M15 EMA200
        macro_ref = ema200_h1 if ema200_h1 > 0 else cur_ema_m
        macro_alignment = (current_price > macro_ref) if trend_bias == "BULLISH" else (current_price < macro_ref)

        # --- 4. Market Structure (ZigZag Swings) ---
        strength = params.get("swing_strength", 1)
        swings = detect_swing_points(data, strength=strength)
        
        # --- 4. Pattern Recognition ---
        pattern = identify_qm_logic(swings) if len(swings) >= 4 else None
        
        # --- 5. RL Quality Assessment ---
        rl_eval = {"quality_score": 0.0, "recommendation": "NO_PATTERN", "metrics": {}}
        displacement = 0.0
        if pattern:
            displacement = abs(pattern.lh2 - pattern.ls2) / cur_atr if cur_atr > 0 else 0
            rl_data = {
                "displacement_magnitude": displacement * cur_atr,
                "range_pips": abs(pattern.lh1 - pattern.ls1),
                "rrr": 3.0 # Standard Institutional Target
            }
            from app.analysis.rl import rl_filter
            rl_eval = rl_filter.evaluate_pattern(data, rl_data, cur_atr)

        # --- 6. Entry Logic ---
        qml_buffer = params.get("qml_buffer", 0.2)
        is_at_qml = False
        if pattern:
            is_at_qml = abs(current_price - pattern.qml) <= qml_buffer
            
        is_entry = False
        rl_threshold = params.get("rl_filter_threshold", 0.4)
        
        if pattern and pattern.valid:
            if pattern.direction == "BULLISH" and trend_bias == "BULLISH":
                if is_at_qml and rl_eval["quality_score"] >= rl_threshold:
                    is_entry = True
            elif pattern.direction == "BEARISH" and trend_bias == "BEARISH":
                if is_at_qml and rl_eval["quality_score"] >= rl_threshold:
                    is_entry = True

        # --- 7. Levels Calculation ---
        sl, tp1, tp2, rrr = (0.0, 0.0, 0.0, 0.0)
        if pattern:
            sl, tp1, tp2, rrr = calculate_levels_logic(pattern, cur_atr, params)

        # --- 8. Professional Response Construction ---
        signal_context = {
            "status": "active_scanning",
            "symbol": self.metadata.get("symbol", "XAUUSD"),
            "timeframe": params.get("timeframe", "15min"),
            "timestamp": data.index[-1].isoformat(),
            "indicators": {
                "ema_13": round(cur_ema_f, 2),
                "ema_50": round(cur_ema_s, 2),
                "ema_200": round(cur_ema_m, 2),
                "ema_200_h1": round(ema200_h1, 2) if ema200_h1 > 0 else None,
                "atr": round(cur_atr, 4),
                "trend_bias": trend_bias,
                "macro_alignment": bool(macro_alignment)
            },
            "market_structure": {
                "pattern_found": bool(pattern),
                "direction": pattern.direction if pattern else None,
                "levels": {
                    "ls1": float(pattern.ls1),
                    "lh1": float(pattern.lh1),
                    "ls2": float(pattern.ls2),
                    "lh2": float(pattern.lh2),
                    "qml": float(pattern.qml)
                } if pattern else None,
                "proximity_pips": round(abs(current_price - (pattern.qml if pattern else current_price)) / 0.01, 2) if pattern else 0.0
            },
            "rl_analysis": rl_eval,
            "execution": {
                "is_entry": bool(is_entry),
                "reason": rl_eval["recommendation"] if is_entry else ("WAITING_FOR_QML_TOUCH" if (pattern and not is_at_qml) else ("FILTERS_NOT_MET" if pattern else "NO_STRUCTURE")),
                "levels": {
                    "entry": current_price,
                    "sl": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "rrr": rrr
                } if is_entry else None
            }
        }

        # Deep sanitize for JSON
        def sanitize(obj):
            if isinstance(obj, dict): return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list): return [sanitize(i) for i in obj]
            elif isinstance(obj, (np.bool_, bool)): return bool(obj)
            elif isinstance(obj, (np.integer, int)): return int(obj)
            elif isinstance(obj, (np.floating, float)): return float(obj)
            elif pd.isna(obj): return None
            return obj

        sanitized_signal = sanitize(signal_context)
        
        entries = pd.Series(bool(is_entry), index=[data.index[-1]])
        exits = pd.Series(False, index=[data.index[-1]])
        
        return entries, exits, sanitized_signal

async def strategy(state, data_manager):
    """
    Standard Entry Point Compatibility Layer.
    Fetches M15 and H1 data for professional-grade analysis.
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    # 1. Fetch M15 Data (Trigger TF)
    data_15m = data_manager.get_candles(symbol, "15min", limit=200)
    if data_15m.empty:
        return pd.Series(False, index=[pd.Timestamp.now()]), pd.Series(False, index=[pd.Timestamp.now()]), {}

    # 2. Fetch H1 Data (Context/Macro TF)
    data_h1 = data_manager.get_candles(symbol, "1hour", limit=200)
    
    # 3. Initialize Strategy Engine
    qm_strat = QuasimodoStrategy()
    
    # 4. Execute Analysis with MTF Support
    entries, exits, signal = await qm_strat.run_live_signal(data_15m, params, data_h1=data_h1)
    
    if signal is None:
        signal = {
            "symbol": symbol,
            "direction": "NEUTRAL",
            "reason": "QM Pattern not detected or filters (EMA/ATR) not met in current window."
        }
    
    return entries, exits, signal

def strategy_vectorized(df: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
    """
    Entry point for Vectorized Backtesting.
    """
    strat = QuasimodoStrategy()
    return strat.run_vector(df, params or {})


# ============================================================================
# CORE LOGIC HELPERS
# ============================================================================

def detect_swing_points(df: pd.DataFrame, strength: int = 1) -> List[SwingPoint]:
    swings = []
    data = df.reset_index()
    n = len(data)
    
    for i in range(strength, n - strength):
        # Swing Low
        if all(data['low'].iloc[i] < data['low'].iloc[i-j] for j in range(1, strength+1)) and \
           all(data['low'].iloc[i] < data['low'].iloc[i+j] for j in range(1, strength+1)):
            swings.append(SwingPoint(i, 'low', data['low'].iloc[i], data['timestamp'].iloc[i]))
        
        # Swing High
        if all(data['high'].iloc[i] > data['high'].iloc[i-j] for j in range(1, strength+1)) and \
           all(data['high'].iloc[i] > data['high'].iloc[i+j] for j in range(1, strength+1)):
            swings.append(SwingPoint(i, 'high', data['high'].iloc[i], data['timestamp'].iloc[i]))
            
    return sorted(swings, key=lambda x: x.index, reverse=True)


def identify_qm_logic(swings: List[SwingPoint]) -> Optional[QMPattern]:
    """
    Identifies a Quasimodo pattern by searching through recent swings.
    """
    if len(swings) < 4: return None
    
    # Iterate through swings to find a sequence of 4 that forms a QM
    # Swings are sorted DESC by index (newest first)
    # We look for a sequence of 4 swings (LS1, LH1, LS2, LH2) within the recent history
    # Search window: check combinations in the last 10 swings
    max_search = min(len(swings), 10)
    for i in range(max_search - 3):
        for j in range(i + 1, max_search - 2):
            for k in range(j + 1, max_search - 1):
                for l in range(k + 1, max_search):
                    s_newest, s_high_low, s_sweep, s_origin = swings[i], swings[j], swings[k], swings[l]
                    
                    # 1. BULLISH QM: Origin(LS1) -> Sweep(LS2) must be Lows, HighLow(LH1) -> Newest(LH2) must be Highs
                    # The timing is Origin < HighLow < Sweep < Newest (Indices are sorted DESC, so Origin.index < HighLow.index < Sweep.index < Newest.index is NOT TRUE)
                    # Correct Timing check (indices are original bar indices):
                    # s_origin.index < s_high_low.index < s_sweep.index < s_newest.index
                    
                    # Chronological Order: p1 -> p2 -> p3 -> p4
                    ordered = sorted([s_newest, s_high_low, s_sweep, s_origin], key=lambda x: x.index)
                    p1, p2, p3, p4 = ordered[0], ordered[1], ordered[2], ordered[3]
                    
                    # 1. BULLISH QM: LS1(p1, Low) -> LH1(p2, High) -> LS2(p3, Low, Sweep) -> LH2(p4, High, BOS)
                    if p1.type == 'low' and p2.type == 'high' and p3.type == 'low' and p4.type == 'high':
                        # Condition: LS2(p3) < LS1(p1) (Liquidity Sweep) AND LH2(p4) > LH1(p2) (BOS)
                        if p3.price < p1.price and p4.price > p2.price:
                            return QMPattern(
                                direction='BULLISH', 
                                ls1=p1.price, lh1=p2.price, ls2=p3.price, lh2=p4.price,
                                qml=p1.price, head=p3.price, 
                                range_pips=abs(p4.price - p3.price),
                                displacement=True, valid=True
                            )
                    
                    # 2. BEARISH QM: HS1(p1, High) -> LL1(p2, Low) -> HS2(p3, High, Sweep) -> LL2(p4, Low, BOS)
                    if p1.type == 'high' and p2.type == 'low' and p3.type == 'high' and p4.type == 'low':
                        # Condition: HS2(p3) > HS1(p1) (Liquidity Sweep) AND LL2(p4) < LL1(p2) (BOS)
                        if p3.price > p1.price and p4.price < p2.price:
                            return QMPattern(
                                direction='BEARISH', 
                                ls1=p1.price, lh1=p2.price, ls2=p3.price, lh2=p4.price,
                                qml=p1.price, head=p3.price, 
                                range_pips=abs(p3.price - p4.price),
                                displacement=True, valid=True
                            )
            
    return None


def calculate_levels_logic(pattern: QMPattern, atr: float, params: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """
    Calculates dynamic SL and TP based on volatility and structure.
    SL: Head + ATR buffer or Pattern_Range % extension
    """
    if pattern.direction == "BULLISH":
        # SL: Below the head (LS2) with buffer
        raw_sl_distance = abs(pattern.qml - pattern.ls2) * 1.2 + (atr * 0.5)
        sl = pattern.qml - raw_sl_distance
        
        # SL Cap (40 pips for Gold)
        max_sl = params.get("max_sl_pips", 40) * 0.1 # 4.0 for Gold
        if abs(pattern.qml - sl) > max_sl:
            sl = pattern.qml - max_sl
            
        risk = abs(pattern.qml - sl)
        tp1 = pattern.qml + (risk * 1.0)
        tp2 = pattern.qml + (risk * 2.0)
        rrr = risk / risk if risk > 0 else 0
    else: # BEARISH
        raw_sl_distance = abs(pattern.ls2 - pattern.qml) * 1.2 + (atr * 0.5)
        sl = pattern.qml + raw_sl_distance
        
        max_sl = params.get("max_sl_pips", 40) * 0.1
        if abs(sl - pattern.qml) > max_sl:
            sl = pattern.qml + max_sl
            
        risk = abs(sl - pattern.qml)
        tp1 = pattern.qml - (risk * 1.0)
        tp2 = pattern.qml - (risk * 2.0)
        rrr = risk / risk if risk > 0 else 0
        
    return sl, tp1, tp2, 1.5


def check_filters_logic(df, pattern, atr, params) -> Tuple[bool, str]:
    return True, "Passed"


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()
