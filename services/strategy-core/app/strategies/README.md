# Strategy Core - Feature Documentation

The `strategy-core` service automatically calculates a rich set of technical features for every candle and publishes them to Redis (`market.alpha.stream`). 

These features are calculated by the `IndicatorWorker` using the `FeatureExtractor` class and can be used by strategies, the AI Analyst, and the Frontend.

## Available Features (JSON Keys)

These keys are available in the `features` JSON object published to Redis.

### Standard Indicators

| Key | Description |
| :--- | :--- |
| `rsi_14` | Relative Strength Index (14 period) |
| `atr_14` | Average True Range (14 period) |
| `ema_9`, `ema_20`, `ema_50`, `ema_200` | Exponential Moving Averages |
| `volatility` | 20-period standard deviation of percent returns |
| `macd` | MACD Line (12, 26, 9) |
| `macd_signal` | MACD Signal Line |
| `macd_hist` | MACD Histogram |
| `bb_upper`, `bb_middle`, `bb_lower` | Bollinger Bands (20, 2.0) |
| `adx` | Average Directional Index (14) |
| `di_plus`, `di_minus` | Directional Indicators (+DI, -DI) |

### Price Action & Structure

| Key | Description |
| :--- | :--- |
| `high_20`, `low_20` | Highest High / Lowest Low of last 20 candles (Donchian) |
| `swing_high` | Price of the most recent confirmed Swing High |
| `swing_low` | Price of the most recent confirmed Swing Low |

### Smart Money Concepts (SMC) Object

The `smc` key contains a nested object with advanced structure data:

```json
"smc": {
    "structure": {
        "pivots": [...],       // Raw pivot points
        "labels": [...]        // Market Structure Labels (HH, LH, LL, HL)
    },
    "order_blocks": [          // Array of Order Blocks
        { "type": "bullish", "top": 1.12, "bottom": 1.11, "mitigated": false }
    ],
    "fvgs": [                  // Array of Fair Value Gaps
        { "type": "bearish", "top": 1.10, "bottom": 1.09 }
    ],
    "liquidity_sweeps": [      // Array of Liquidity Sweeps
        { "type": "bullish_sweep", "level": 1.08 }
    ]
}
```

## How to Use in Strategy (Example)

Strategies running in contexts that receive this pre-calculated data can access it directly to simplify logic.

**Hypothetical Example:**

```python
import pandas as pd
import vectorbt as vbt
# Assuming access to internal libs for advanced Logic
from app.indicators import detect_liquidity_sweeps 

METADATA = {
    "name": "SMC Trend Reversal",
    "description": "Combines EMA Trend with Liquidity Sweeps and RSI.",
    "defaults": { "ema_period": 200, "rsi_period": 14 }
}

def strategy(data: pd.DataFrame, params: dict = None):
    """
    Advanced Strategy using SMC Features + Standard Indicators
    """
    if params is None: params = {}
    
    close = data['close']
    
    # 1. Trend Filter (EMA 200)
    # Check if 'ema_200' exists (Pre-calc) or calculate it
    if 'ema_200' in data.columns:
        ema_200 = data['ema_200']
    else:
        ema_200 = vbt.MA.run(close, 200).ma
        
    bullish_trend = close > ema_200
    
    # 2. Liquidity Sweeps (SMC Feature)
    # Use internal shared logic to detect sweeps dynamically
    sweeps = detect_liquidity_sweeps(data)
    
    # Map sweeps to a Series for vectorization
    sweep_signal = pd.Series(False, index=close.index)
    for s in sweeps:
        if s['type'] == 'bullish_sweep':
             # Use index relative to the sliced dataframe
             idx = s['index']
             if 0 <= idx < len(close):
                 sweep_signal.iloc[idx] = True
                 
    # 3. Momentum (RSI)
    if 'rsi_14' in data.columns:
        rsi = data['rsi_14']
    else:
        rsi = vbt.RSI.run(close, 14).rsi
        
    oversold = rsi < 35
    
    # 4. Entry Logic
    # Bullish Trend + Sweep (Liquidity Grab) + RSI Oversold condition
    entries = bullish_trend & sweep_signal & oversold
    
    # Exit if RSI Overbought
    exits = rsi > 70
    
    # 5. Live Signal Construction
    latest_signal = {
        "direction": "BULLISH" if bool(entries.iloc[-1]) else "FLAT",
        "reason": "SMC Liquidity Grab in Uptrend",
        "metadata": {
            "strategy": METADATA["name"],
            "ema_200": float(ema_200.iloc[-1]) if pd.notna(ema_200.iloc[-1]) else 0.0,
            "sweeps_count": len(sweeps)
        }
    }
    
    return entries, exits, latest_signal
```
