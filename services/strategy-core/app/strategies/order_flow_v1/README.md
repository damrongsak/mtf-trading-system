
# Order Flow V1

## Description
A "Data-Driven" strategy that uses Auction Market Theory to identify institutional footprint.
It analyzes Order Flow (Footprint) data to detect:
1.  **Aggressive Imbalance**: Buy Volume significantly exceeding Sell Volume at specific price levels.
2.  **Absorption**: High volume with little price movement.

## Logic (Buy Only)
1.  **Macro Filter**: Price must be above EMA 200.
2.  **Trigger**: 
    -   Candle contains an **Aggressive Imbalance** (Ask Vol > Bid Vol * Ratio).
    -   *Future enhancement: Waif for pullback into the imbalance zone.*

## Parameters
*   `ema_period`: Period for the trend filter (default: 200).
*   `imbalance_ratio`: Ratio of Ask/Bid volume to define imbalance (default: 3.0).
*   `sl_pips`: Fixed Stop Loss in pips.
*   `tp_pips`: Fixed Take Profit in pips.

## AI Metadata
*   `trend_ok`: Boolean indicating if macro trend is bullish.
*   `imbalance_detected`: Boolean indicating if footprint imbalance was found.
