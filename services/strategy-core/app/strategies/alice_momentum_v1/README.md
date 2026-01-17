# Alice Momentum Strategy (Regime V1)

## Description
A modular Trend Following / Regime Switching strategy. It uses **Regime Classification** (Easy, Normal, Hard, Nightmare) based on EMA alignment and Volatility to select appropriate sub-systems.

## Modules

### A. Regime Classifier
*   **Metric**: Alignment of EMA 50/100/200 and ATR Spike.
*   **States**:
    *   `EASY/NORMAL`: Trend Aligned (50 > 100 > 200).
    *   `HARD`: Entangled / Ranging.
    *   `NIGHTMARE`: ATR > 2x Average ATR.

### B. Signal Generator
*   **System A (Breakout)**: Active in `EASY/NORMAL`. Triggers on 20-period Donchian Breakout with MACD confirmation.
*   **System B (Buy on Dip)**: Active in `NORMAL`. Triggers when price touches EMA 100 zone and rejects.
*   **System C (Channel)**: Disabled in V1.
*   **System D (Safety)**: No entries in `NIGHTMARE`.

## Parameters
*   `ema_fast`: 50
*   `ema_medium`: 100
*   `ema_slow`: 200
*   `breakout_period`: 20
*   `atr_period`: 14
*   `risk_per_trade`: 1%

## AI Metadata
*   `regime`: The current detected market state (EASY, NORMAL, HARD, NIGHTMARE).
*   `technical`: EMA values and ATR.
