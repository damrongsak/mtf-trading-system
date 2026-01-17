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
3.  **Deploy**:
    *   **Generic**: Use the `ALPHA_ENGINE_V1` template.
        *   Config: `{ "formula": "..." }`
    *   **Hybrid**: Use the `HYBRID_ALPHA_V1` template.
        *   Config: `{ "alpha_threshold": 0.8 }`

---

## Method 2: Standard Strategy Workflow (Unified)
This is the recommended workflow for production-grade strategies. It combines the speed of the **Visual Editor** with the power of **File-Based Plugins**.

### Phase 1: Prototype in Visual Editor (Method 3)
Start by prototyping your logic in the interactive editor.

1.  **Access**: [http://localhost:3000/strategies/editor](http://localhost:3000/strategies/editor).
2.  **Code Logic**: Write a standard `def strategy(data, params)` function using VectorBT.
    ```python
    import vectorbt as vbt
    def strategy(data, params=None):
        if params is None: params = {}
        close = data['close']
        sma = vbt.MA.run(close, int(params.get('period', 20)))
        return sma.ma_crossed_above(close), sma.ma_crossed_below(close)
    ```
3.  **Verify**: Run backtests and optimizations until satisfied.
4.  **Save**: Click the "Save" icon to keep a copy in the library.

### Phase 2: Create Production Plugin (Method 2)
Once your logic is proven, migrate it to the codebase for deployment.

1.  **Create Directory**: `services/strategy-core/app/strategies/<my_strategy_v1>/`
2.  **Create File**: `services/strategy-core/app/strategies/<my_strategy_v1>/strategy.py`
## 2. The Standard Method (Unified Interface)

We now use a **Single Function** architecture. You write one synchronous, vectorized function, and the system handles the rest:
- **Editor/Backtest**: Runs your function directly against historical data.
- **Live Execution**: The engine **automatically wraps** your function, fetches 1 year of historical data, and extracts the latest signal for real-time trading.

### Step 1: Write the Strategy
Create a `strategy.py` file (or use the Editor) with this exact signature:

```python
import vectorbt as vbt
import pandas as pd
import numpy as np

# Metadata for the Registry
METADATA = {
    "name": "Moving Average Cross V2",
    "description": "Standardized MA Crossover Strategy",
    "defaults": {
        "period": 14,
        "slow_period": 30
    }
}

def strategy(data, params=None):
    """
    Unified Strategy Function
    Args:
        data: pd.DataFrame (ohlcv)
        params: dict of parameters
    Returns:
        entries, exits, signal_dict
    """
    if params is None: params = {}
    period = int(params.get("period", 14))
    slow_period = int(params.get("slow_period", 30))
    
    close = data['close']
    
    # 1. Calculate Indicators (Vectorized)
    fast_ma = vbt.MA.run(close, period)
    slow_ma = vbt.MA.run(close, slow_period)
    
    # 2. Generate Signals (Series)
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    # 3. Return Protocol: (Entries, Exits, Signal_Dict)
    # The Engine automatically extracts the LATEST signal for Live Trading.
    latest_signal = {
        "direction": "BULLISH" if entries.iloc[-1] else "BEARISH",
        "stop_loss": float(slow_ma.ma.iloc[-1]), # Example SL logic
        "reason": "MA Crossover",
        "metadata": {
            "strategy_name": METADATA["name"],
            "fast_ma": float(fast_ma.ma.iloc[-1]),
            "slow_ma": float(slow_ma.ma.iloc[-1]),
            "confidence": 0.85
        }
    }
    
    return entries, exits, latest_signal
```

### Step 2: Deployment
1.  **Save File**: Place in `services/strategy-core/app/strategies/<your_strategy>/strategy.py`.
2.  **Hot Reload**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/strategies/reload
    ```
3.  **Done!**
    - **Backtest**: Go to Frontend -> Backtest -> Select "Moving Average Cross V2". It works instantly.
    - **Live**: Go to Frontend -> Bot -> Deploy "Moving Average Cross V2". The engine auto-wraps it.
