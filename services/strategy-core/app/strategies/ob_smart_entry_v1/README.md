# Order Block Smart Entry Strategy (v1)

Professional multi-timeframe strategy optimized for mechanical entry within institutional zones.

## Logic Overview

1.  **Trend Bias (H1)**: Established using EMA 50 vs EMA 200.
    - `Bullish`: EMA 50 > EMA 200
    - `Bearish`: EMA 50 < EMA 200
2.  **Point of Interest (M15)**: Identifies unmitigated Order Blocks (OB). 
    - The strategy only activates if price is currently testing an OB aligned with the trend bias.
3.  **Entry Trigger (M5)**: Executes on a high-probability candlestick close.
    - `Long`: M5 Close crosses above EMA 20 while in a Bullish OB zone.
    - `Short`: M5 Close crosses below EMA 20 while in a Bearish OB zone.

## Parameters

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `tf_trend` | `1h` | Timeframe for long-term trend bias. |
| `tf_setup` | `15min` | Timeframe for Order Block detection. |
| `ema_trend_fast` | `50` | Fast EMA period for trend. |
| `ema_trend_slow` | `200` | Slow EMA period for trend. |
| `ema_trigger` | `20` | EMA period for LTF entry trigger. |
| `rr_ratio` | `2.0` | Target reward-to-risk ratio. |

## Performance Notes

-   **Vectorized Proof**: All indicator calculations (EMA, ATR, OB) are fully vectorized using `vectorbt` and `numpy`.
-   **Zero-Lag I/O**: Signal notifications are pushed asynchronously to Telegram via the plugin system.
-   **Memory Capped**: Buffers are limited to the minimum required for EMA 200 windowing.
