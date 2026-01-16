# Volatility Breakout Strategy (V1)

## Description
This strategy captures explosive price movements ("Expansion") that typically follow periods of low volatility ("Compression"). It is based on the concept that markets alternate between range-bound (low volatility) and trending (high volatility) phases.

## Formula
### 1. Compression Detection
The strategy identifies a "Setup" when market volatility is significantly lower than average.
*   **Condition A**: Current `ATR(14)` < `SMA(ATR(14), 20)` (Current volatility below long-term average).
*   **Condition B**: Current Daily Range < `ADR(20)` (Average Daily Range).

### 2. Trigger (Breakout)
The strategy enters a trade when price breaks out of a dynamic channel defined by the Keltner Channels.
*   **Upper Band**: `EMA(20) + (Multipler * ATR(14))`
*   **Lower Band**: `EMA(20) - (Multipler * ATR(14))`
*   **Buy Signal**: Price Close > Upper Band
*   **Sell Signal**: Price Close < Lower Band

### 3. Risk Management
*   **Stop Loss**: Entry Price +/- (`2.0 * ATR`)
*   **Take Profit**: Entry Price +/- (`1.0 * ADR`)

## Parameters
| Parameter | Default | Description |
| :--- | :--- | :--- |
| `atr_period` | 14 | Lookback period for ATR (Volatility) |
| `atr_smooth_period` | 20 | Lookback period for SMA of ATR (historical baseline) |
| `adr_period` | 20 | Lookback period for ADR (Daily Range) |
| `keltner_mult` | 2.0 | Multiplier for Keltner Channel width |

## AI Metadata Schema
The strategy outputs a rich metadata object for the AI Analyst to generate narrative briefings.

```json
{
  "signal_timestamp": "2024-01-01T10:00:00", // Timestamp of the candle that triggered the signal
  "volatility": {
    "atr_14": 1.5,      // Current ATR Value
    "adr_20": 2.0,      // Current ADR Value
    "compression_ratio": 0.75, // ratio = current_atr / sma_atr (if < 1.0, was compressed)
    "regime": "EXPANSION (Exiting Compression)" // Textual description of state
  },
  "technical": {
    "breakout_level": 2050.50, // Price at breakout
    "keltner_upper": 2055.0,
    "keltner_lower": 2045.0
  }
}
```
