from typing import Dict, Any, List
import pandas as pd
from app.schemas import IndicatorInterpretation

def get_rsi_interpretation(rsi_value: float, window: int) -> IndicatorInterpretation:
    """Standard Institutional RSI Interpretation."""
    bias = "NEUTRAL"
    strength = 0.5
    summary = "RSI is in neutral territory."
    advice = "Maintain current positions; no immediate overbought/oversold signal."

    if rsi_value > 70:
        bias = "BEARISH"
        strength = (rsi_value - 70) / 30 + 0.5
        summary = f"RSI is Overbought ({round(rsi_value, 2)})"
        advice = "Watch for bearish reversals or exhaustion. Avoid new long entries."
    elif rsi_value < 30:
        bias = "BULLISH"
        strength = (30 - rsi_value) / 30 + 0.5
        summary = f"RSI is Oversold ({round(rsi_value, 2)})"
        advice = "Watch for bullish reversals. Potential accumulation zone."
    
    return IndicatorInterpretation(
        summary=summary,
        bias=bias,
        strength=min(strength, 1.0),
        ai_advice=advice
    )

def get_atr_interpretation(atr_value: float, close_price: float) -> IndicatorInterpretation:
    """Standard Institutional ATR Interpretation."""
    vol_pct = (atr_value / close_price) * 100
    
    summary = f"ATR is {round(atr_value, 2)} ({round(vol_pct, 2)}% of price)."
    bias = "NEUTRAL"
    strength = 0.5
    advice = "Use ATR for dynamic stop-loss placement (e.g., 1.5x - 2.0x ATR)."
    
    if vol_pct > 2.0:
        advice = "High volatility detected. Reduce position sizing to maintain fixed risk."
    elif vol_pct < 0.5:
        advice = "Low volatility. Expect range-bound behavior or a possible breakout squeeze."
        
    return IndicatorInterpretation(
        summary=summary,
        bias=bias,
        strength=strength,
        ai_advice=advice
    )

def get_macd_interpretation(macd: float, signal: float, hist: float) -> IndicatorInterpretation:
    """Standard Institutional MACD Interpretation."""
    bias = "NEUTRAL"
    strength = 0.5
    summary = "MACD and Signal line are in convergence."
    advice = "No clear momentum shift."

    if macd > signal and hist > 0:
        bias = "BULLISH"
        strength = 0.7
        summary = "Bullish Momentum (MACD > Signal)"
        advice = "Momentum is accelerating to the upside."
    elif macd < signal and hist < 0:
        bias = "BEARISH"
        strength = 0.7
        summary = "Bearish Momentum (MACD < Signal)"
        advice = "Momentum is accelerating to the downside."
        
    return IndicatorInterpretation(
        summary=summary,
        bias=bias,
        strength=strength,
        ai_advice=advice
    )
