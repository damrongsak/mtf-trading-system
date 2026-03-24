# Quasimodo V2 Strategy (QM-v2)

## 📋 Overview
**Quasimodo V2** is a professional-grade evolution of the classic QM pattern, optimized for **XAU/USD (Gold)**. It combines institutional market structure analysis with **Multi-Timeframe (MTF)** confluence and **Deep Reinforcement Learning (RL)** signal quality filtering.

The strategy identifies "Smart Money" footprints where price sweeps a previous swing point, breaks structure with high displacement, and returns to the "Quasimodo Level" (QML) for a high-probability entry aligned with the macro trend.

## 🏗️ Logic & Patterns (V2 Enhancements)
1.  **Macro Bias (H1):** Institutional EMA 200 alignment. Price must be above/below H1 EMA 200 for Bullish/Bearish bias.
2.  **Professional Telemetry:** Every logic "tick" exports high-fidelity metrics for 3rd party monitoring (see API section).
3.  **RL-Quality Filter:** Uses a pre-trained Reinforcement Learning agent to score pattern quality based on:
    *   **Displacement Magnitude**: The strength of the BOS leg relative to ATR.
    *   **Session Timing**: Alignment with London/New York volatility.
    *   **Structure Clarity**: Proximity of the return to the exact QML.

## ⚙️ Parameters (V2)
| Parameter | Default | Description |
| :--- | :--- | :--- |
| `risk_pct` | `0.01` | Dynamic risk per trade (1.0% of NAV). |
| `ema_fast` | `13` | Fast EMA (M15) for entry alignment. |
| `ema_slow` | `50` | Slow EMA (M15) for structure alignment. |
| `ema_macro` | `200` | Macro EMA for H1 trend filter. |
| `rl_filter_threshold` | `0.40` | Min score (0-1) required for signal qualification. |
| `qml_buffer` | `0.2` | Tolerance for price reaching the QML. |

## 🌐 Professional API Integration
Quasimodo V2 supports external monitoring via the REST API.

### Enriched Signal Payload
When triggering a manual tick or receiving a signal, the following schema is provided:
- `indicators`: M15/H1 EMA confluence, ATR, and Macro Bias status.
- `market_structure`: Exact coordinates (LS1, LH1, LS2, LH2) and QML.
- `rl_analysis`: AI confidence score and diagnostic verdict.
- `execution`: Institutional entry/SL/TP levels with RRR calculation.

## 🛡️ Institutional Risk Management
- **Volatility-Adjusted Stop Loss:** SL is calculated as `(Pattern_Range * 1.2) + (ATR * 0.5)`.
- **Dynamic Lot Scaling:** Automated 100k standard unit conversion via `UnitConverter`.
- **Shadow Mode Support:** Fully verified for institutional "Shadow Run" monitoring.

---
*Standard: MTF Olympus v2.2 (Professional Grade)*
