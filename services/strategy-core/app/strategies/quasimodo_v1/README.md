# Quasimodo V1 Strategy (QM-v1)

## 📋 Overview
**Quasimodo V1** is an institutional-grade trading strategy designed for XAU/USD (Gold). it implements a high-probability reversal pattern based on **Liquidity Sweeps (LS)** and **Break of Structure (BOS)**, combined with **Multi-Timeframe (MTF)** confluence.

The strategy identifies "Smart Money" footprints where price sweeps a previous swing point, breaks the immediate structure with displacement, and returns to the "Quasimodo Level" (QML/QMH) for entry.

## 🏗️ Logic & Patterns
1.  **Macro Bias (H1):** EMA 50/200 alignment. Price must be above/below EMA 200 for Bullish/Bearish bias.
2.  **Pattern Structure (M15/H1):**
    - **LS1 -> LH1 -> LS2 (Sweep) -> LH2 (BOS):** For Bullish QM.
    - **HS1 -> LL1 -> HS2 (Sweep) -> LL2 (BOS):** For Bearish QM.
3.  **Entry Trigger (M15):** 
    - Price returns to LS1/HS1 (The QM Level).
    - EMA 13 alignment.
    - "Strong Body" candle confirmation (Body > 50% of Range).
4.  **Displacement Check:** All BOS legs must have a High-Volume/Large-Body expansion.

## ⚙️ Parameters
| Parameter | Default | Description |
| :--- | :--- | :--- |
| `risk_pct` | `0.01` | Dynamic risk per trade (1.0% of NAV). |
| `ema_fast` | `13` | Fast EMA for entry alignment. |
| `ema_slow` | `50` | Slow EMA for structure alignment. |
| `min_rrr` | `1.5` | Minimum Risk-Reward Ratio required. |
| `atr_period` | `14` | ATR period for volatility-adjusted Stop Loss. |
| `max_sl_pips`| `40` | Hard cap on SL distance (Institutional Guardrail). |
| `swing_strength`| `2` | ZigZag strength for swing point detection. |

## 🛠️ Requirements & Setup
- **Symbols:** Optimized for `XAU_USD`.
- **Timeframes:**
    - `H1`: Macro Structure & Trend.
    - `M15`: Pattern Setup & Entry Trigger.
- **Data:** Requires OHLCV data with at least 200 candles for EMA calculation.

## 🛡️ Risk Management
- **Stop Loss:** Volatility-adjusted: `(Pattern_Range * 1.2) + (ATR * 0.5)`.
- **Take Profit (Multi-Target):**
    - TP1: 1.0R (Move SL to Breakeven).
    - TP2: 2.0R.
    - TP3: Runner with Trailing SL.

---
*Standard: MTF Olympus v2.0*
