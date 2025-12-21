# MTF Trading System - Execution Rules & Logic
# Source of Truth for Strategy and Risk Engine

## 1. Overview
This document defines the strict logical rules for the "Phoenix" XAU/USD trading strategy. These rules are implemented in the `strategy-core` service (`app/logic.py`, `app/smc.py`) and the `execution` service (`app/executor.py`). Any deviation between this document and the code is a bug.

## 2. Market Structure & Timeframes
The strategy utilizes a Multi-Timeframe (MTF) approach to align momentum with the higher-timeframe trend.

| Role | Timeframe | Purpose |
| :--- | :--- | :--- |
| **Macro** | 4H / Daily | Defines the overall directional bias (Trend). |
| **Setup** | 1H | Identifies high-probability areas of interest (Order Blocks). |
| **Trigger** | 15m | Confirms entry with momentum and precise candle formations. |

---

## 3. Signal Generation Rules

### Rule A: Macro Bias (Trend Filter)
**Context:** 4H or Daily Chart
**Function:** `check_macro_bias` in `logic.py`

1.  **Indicator:** Exponential Moving Average (EMA) with period 200 on the 4H timeframe.
2.  **Logic:**
    *   **BULLISH:** The last closed 4H candle's Close Price > 4H EMA(200).
    *   **BEARISH:** The last closed 4H candle's Close Price < 4H EMA(200).
    *   **NEUTRAL:** Insufficient data or undefined state.
3.  **Constraint:** If the bias is NEUTRAL, no trades are taken.

### Rule B: Setup Zone (Confluence)
**Context:** 1H Chart
**Function:** `check_setup_zone` in `logic.py` & `detect_order_blocks` in `smc.py`

1.  **Concept:** Price must be inside a valid **Order Block (OB)** aligned with the Macro Bias.
2.  **Order Block Definition:**
    *   **Bullish OB:** The last down candle (Red) before a strong up move (Green) that breaks structure/displaces price.
        *   *Validation:* Current Close > Prev Open AND Current Body > 1.5 * Prev Body.
    *   **Bearish OB:** The last up candle (Green) before a strong down move (Red).
        *   *Validation:* Current Close < Prev Open AND Current Body > 1.5 * Prev Body.
    *   **Volume Filter:** The impulsive move should ideally have higher volume than the 20-period average (if volume data is available).
3.  **Zone Logic:**
    *   The system scans for unmitigated Order Blocks on the 1H timeframe.
    *   **Signal Valid If:** Current 1H Close Price is physically inside the price range (High-Low) of an active OB matching the Macro Bias.
        *   *Bullish:* Price inside Bullish OB.
        *   *Bearish:* Price inside Bearish OB.

### Rule C: Trigger (Entry Confirmation)
**Context:** 15m Chart
**Function:** `check_trigger` in `logic.py`

1.  **Concept:** A "Vector Candle" confirming momentum in the trade direction.
2.  **Logic:**
    *   Analyze the **last completed** 15m candle.
    *   **Body-to-Wick Ratio (Rv):** `Body Length / Total Range`.
    *   **Threshold:** Rv must be >= **0.70** (configurable).
3.  **Direction Check:**
    *   **Long:** Candle must be Green (Close > Open).
    *   **Short:** Candle must be Red (Close < Open).

---

## 4. Risk Management Rules (The "Iron Guardrail")

These rules are enforced by the `Execution Service` and cannot be overridden by the strategy.

### Rule D: Dynamic Stop Loss
**Function:** `calculate_stop_loss` in `logic.py`

1.  **Based on Volatility:** Uses the Average True Range (ATR).
2.  **Calculation:**
    *   `ATR_Value` = ATR(14) on 15m timeframe.
    *   `SL_Distance` = `ATR_Value` * `ATR_Multiplier` (Default: 1.75).
3.  **Placement:**
    *   **Long:** Entry Price - SL_Distance.
    *   **Short:** Entry Price + SL_Distance.

### Rule E: Position Sizing & Capital Preservation
**Function:** `can_execute` in `executor.py`

1.  **Max Risk Cap:** **$10.00** per trade (Hard Limit).
2.  **Lot Calculation Formula:**
    ```python
    raw_lot = max_risk_usd / sl_distance_usd
    final_lot = floor(raw_lot, 2 decimals) # e.g., 0.128 -> 0.12
    ```
3.  **Minimum Viable Trade:**
    *   If `final_lot` < **0.01**, the trade is **REJECTED**.
    *   *Reasoning:* Ensures we never over-risk just to fit a trade. If the stop is too wide for $10 risk, we skip.

### Rule F: Volatility Guardrail (Implied)
1.  **Constraint:** If `SL_Distance` is negative or zero, trade is rejected.
2.  **Constraint:** If calculated Lot Size is valid but risk exceeds cap (due to rounding errors), strict inequality checks prevent execution.

---

## 5. Execution Flow Summary

1.  **Ingest:** Data Pipeline fetches latest 15m, 1H, 4H candles.
2.  **Analyze (Strategy Core):**
    *   Check 4H EMA (Rule A).
    *   Check 1H Order Blocks (Rule B).
    *   Check 15m Candle Rv (Rule C).
3.  **Propose:** If A+B+C passed, Strategy Core calculates Entry and SL (Rule D).
4.  **Validate (Execution Service):**
    *   Receive Proposal: `{ risk_usd: 10, sl_dist: ..., min_lot: 0.01 }`.
    *   Calculate Lot Size (Rule E).
    *   Check Constraints (Rule E, F).
5.  **Execute:** If valid, place order via Oanda Adapter.
