# How to Create Custom Trading Algorithms
This guide explains how to add new trading logic to the **MTF Trading System**.

## Overview
The system uses a **Plugin-based Architecture** for strategies. All trading logic resides in the `Strategy Core` service. To add a new algorithm, you simply implement a Python function and register it.

## Quick Start (Developer Flow)

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
        
    # 2. Calculate Indicators (using pandas_ta or vectorbt)
    # Example: Simple Moving Average
    close = df['close']
    sma = close.rolling(50).mean()
    
    # 3. Check Conditions
    current_price = close.iloc[-1]
    current_sma = sma.iloc[-1]
    
    direction = None
    if current_price > current_sma:
         direction = "BULLISH"
    elif current_price < current_sma:
         direction = "BEARISH"
         
    # 4. Return Signal (or None)
    if direction:
        return {
            "direction": direction,
            "stop_loss": current_sma,  # Required
            "reason": f"Price crossed SMA: {direction}"
        }
    return None
```

### 3. Register the Strategy
Add your function to the `StrategyRegistry` class at the bottom of the file.

```python
class StrategyRegistry:
    _strategies = {
        # ... existing ...
        "MY_STRAT_V1": my_custom_strategy  # <--- Add this
    }
    
    _metadata = {
        # ... existing ...
        "MY_STRAT_V1": {
            "name": "My Custom Strategy",
            "description": "Simple SMA Crossover",
            "defaults": {
                "period": 50
            }
        }
    }
```

### 4. Restart the Backend
For the changes to take effect, you must restart the `strategy-core` service:

```bash
docker compose restart strategy-core
```

### 5. Use it in the UI
1. Go to **Dashboard** -> **strategies**.
2. Click **Launch Strategy**.
3. Select **My Custom Strategy** (MY_STRAT_V1) from the Template dropdown.

## Advanced Usage

### Using Multiple Timeframes
You can resample data to get Higher Timeframe (HTF) context.

```python
# Create H1 bars from M15 data
df_h1 = df_base.resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
```

### Using Config Parameters
Access user-defined settings via `state.config_json`:

```python
def my_strategy(state, data_manager):
    config = state.config_json
    rsi_period = config.get('rsi_period', 14) # Default to 14
```

### Stop Loss & Risk
The system handles position sizing automatically based on the user's Risk Settings (e.g., Max Risk $10). Your strategy only needs to provide:
1.  **Direction**: `BULLISH` or `BEARISH`
2.  **Stop Loss Price**: Where the trade fails.

The distance between Entry and Stop Loss determines the position size.

---
**Need Help?**
Check `services/strategy-core/app/indicators.py` for available helper functions like `calculate_rsi` and `calculate_atr`.
