# How to Create Custom Trading Algorithms
This guide explains how to add new trading logic to the **MTF Trading System**.

## Overview
There are two ways to build strategies in Olympus:
1.  **Alpha Engine (Recommended)**: Write statistical factors using safe, concise mathematical formulas. Best for research and signals.
2.  **Strategy Core Plugins (Advanced)**: Write raw Python asyncio functions. Best for complex execution logic or external dependencies.

---

## Method 1: The Alpha Engine (New)

The **Alpha Engine** allows you to design factors without writing full Python modules. Logic is compiled safely by the `Athena` engine.

### 1. Open the Alpha Lab
Navigate to the [Alpha Lab](http://localhost:3000/alpha/lab) in your browser.

### 2. Write Your Formula
Use the Monaco Editor to type your logic using the supported syntax:

**Syntax Reference:**
*   `rank(x)`: Cross-sectional rank (0-1).
*   `delay(x, n)`: Value of x, n periods ago.
*   `ts_max(x, n)` / `ts_min(x, n)`: Rolling max/min.
*   `sma(x, n)` / `std(x, n)`: Rolling mean/std.
*   `correlation(x, y, n)`: Rolling correlation.

**Examples:**
*   **Mean Reversion:** `(close - sma(close, 20)) / std(close, 20)`
*   **Momentum:** `rank(close / delay(close, 10))`
*   **Breakout:** `close > ts_max(high, 20)`

### 3. Test & Deploy
1.  **Sparkline Preview**: Type to see instant shape verification.
2.  **Backtest**: Click "Run Backtest" to see Sharpe/IC metrics.
3.  **Save**: (Coming Soon) Promotes the formula to a registered Strategy.

---

## Method 2: Python Plugins (Advanced)

For logic that requires complex control flow (loops, external APIs) or specific libraries (`pandas-ta`), use the Plugin system.

### 1. Locate the Registry
Open the file:
`services/strategy-core/app/registry.py`

### 2. Define Your Logic
Add a new `async` function that accepts `state` and `data_manager`.

**Template:**
```python
async def my_custom_strategy(state, data_manager):
    """
    My Custom Strategy Description
    """
    symbol = state.symbol
    
    # 1. Fetch Data
    df = data_manager.get_data(symbol)
    if df.empty:
        return None
        
    # 2. Calculate Indicators
    close = df['close']
    sma = close.rolling(50).mean()
    
    # 3. Check Conditions
    if close.iloc[-1] > sma.iloc[-1]:
         return {
            "direction": "BULLISH",
            "stop_loss": sma.iloc[-1],
            "reason": "Price > SMA"
        }
    return None
```

### 3. Register the Strategy
Add your function to the `StrategyRegistry` class.

```python
class StrategyRegistry:
    _strategies = {
        # ... existing ...
        "MY_STRAT_V1": my_custom_strategy
    }
```

### 4. Restart Strategy Core
```bash
docker compose restart strategy-core
```

