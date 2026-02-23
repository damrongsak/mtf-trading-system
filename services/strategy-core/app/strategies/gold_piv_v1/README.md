# Gold PIV Structural Strategy (v1.0)

## 🚀 Overview
The **Gold PIV Structural Strategy** is a high-conviction institutional strategy designed for XAU/USD. It utilizes **Projected Implied Volatility (PIV)** to identify structural overextension and momentum exhaustion, combined with **Smart Money Concepts (SMC)** filters.

The strategy implementation resides in `services/strategy-core/app/strategies/gold_piv_v1/`.

## 🧠 Trading Theory
This strategy is based on **Kirk Northington's Volatility-Based Technical Analysis**. Unlike standard Bollinger Bands or RSI, it uses forward-looking volatility (PIV) to define market "extremes."

### Key Concepts:
1.  **PIV (Projected Implied Volatility)**: Predicted volatility for the upcoming sessions, calculated via GJR-GARCH models or extracted from GVZ (Gold Volatility Index).
2.  **N-Bands**: Dynamic non-linear bands that expand and contract based on PIV. They represent statistical "walls" where price is likely to exhaust.
3.  **True Slope**: A volatility-adjusted measure of price momentum. It identifies when a trend is actually losing steam, rather than just slowing down.

## 🛠️ Strategy Logic

### 1. Macro Bias (H1 Setup)
- **Long Bias**: Current Price > EMA 200 on H1.
- **Short Bias**: Current Price < EMA 200 on H1.

### 2. Entry Conditions (M15 Trigger)
The strategy waits for a "Mean Reversion Confluence" at volatility extremes:
- **BULLISH Signal**:
    - Price touches or breaks below the **Lower N-Band (2.0σ)**.
    - True Slope flips from **Negative to Positive** (Momentum reversal).
    - Prevailing Macro Bias must be **LONG**.
- **BEARISH Signal**:
    - Price touches or breaks above the **Upper N-Band (2.0σ)**.
    - True Slope flips from **Positive to Negative**.
    - Prevailing Macro Bias must be **SHORT**.

### 3. Risk Management
- **Stop Loss**: Set at the recent swing high/low (last 5 candles).
- **Position Sizing**: Optimized for the current volatility regime (Yang-Zhang estimator).

## ⚙️ Configuration
The strategy can be configured via `config_json` in the database or strategy registry:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `tf_trigger` | string | `15min` | The timeframe used for execution triggers. |
| `tf_setup` | string | `1h` | The timeframe used for macro bias and GARCH fitting. |
| `multiplier` | float | `2.0` | The standard deviation multiplier for N-Bands. |
| `piv_prominence` | float | `0.5` | Sensitivity for VBSR level detection. |

## 🚀 How to Use
1.  **Deploy**: Ensure the `strategy-core` service is running with GARCH engine enabled.
2.  **Register**: Add the strategy to the `active_strategies` table with `symbol='XAUUSD'`.
3.  **Backtest**: Run a simulation via the AI Analyst:
    ```bash
    /ask Run a backtest for Gold PIV Structural Strategy on M15 for the last 30 days.
    ```
4.  **Monitor**: Use the PIV Audit tool to see the bands in real-time:
    ```bash
    /ask Volatility Structural Audit (PIV) for Gold.
    ```

---
**Author**: Antigravity (Advanced Agentic Coding Team)
**Context**: MTF Olympus Institutional Quant Suite
