# 5-EMA Recovery Strategy

## Description
A Trend Following + Mean Reversion strategy designed to "recover" a portfolio by taking high-probability trades. It identifies the major trend using EMA 200 and waits for price to pull back to value zones (EMA 25, 50, 100) before entering on momentum confirmation.

## Logic
1.  **Trend Filter**: Price > EMA 200 (Bullish Only for now).
2.  **Setup Zone**: Price pulls back and touches EMA 25, 50, or 100.
3.  **Trigger**: Green Reversal Candle (Close > Open) + RSI Divergence (Price Low < Prev Low, RSI > Prev RSI).

## Parameters
*   `ema_periods`: [10, 25, 50, 100, 200]
*   `rsi_period`: 14
*   `risk_per_trade`: 1.0% (0.01)

## AI Metadata
*   `ema_200`: Value of the major trend line.
*   `rsi`: Current RSI value.
*   `technical`:
    *   `trend_biased`: BULLISH/BEARISH
    *   `in_zone`: Boolean (True if price is in pullback zone)
