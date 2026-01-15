---
name: new-strategy-implementation
description: |
    Use this skill when you need to create, add, or implement a new trading strategy in the `strategy-core` service.
---

# New Strategy Implementation
**Goal:** Create a standardized strategy in `services/strategy-core`.

## Prerequisite
Ensure you have the strategy logic defined (e.g., "RSI < 30 buys").

## Process

1.  **Define Strategy Metadata**
    *   Open `services/strategy-core/app/registry.py`.
    *   Add a new entry to `StrategyRegistry._metadata`.
    *   Define `defaults` (parameters like `rsi_period`, `window`).

2.  **Implement Strategy Function**
    *   In `services/strategy-core/app/registry.py` (or a new file in `app/foundry/` if complex), create the async function:
        ```python
        async def my_new_strategy(state, data_manager):
            # ... implementation ...
        ```
    *   **MUST** return a dict with keys: `direction` ("BULLISH"/"BEARISH"), `stop_loss`, `reason`. Or `None` if no signal.
    *   **MUST** use `data_manager.get_data(symbol)` to fetch data.
    *   **MUST** handle exceptions and return `None` on error (do not crash).

3.  **Register the Strategy**
    *   Add the function to `StrategyRegistry._strategies` map in `registry.py`.

4.  **Add a Unit Test**
    *   Create a new test file: `services/strategy-core/tests/test_strategy_<name>.py`.
    *   Mock `data_manager` and `state`.
    *   Assert that the strategy returns the expected signal for a known data pattern.

## Code Template
```python
async def my_strategy(state, data_manager):
    symbol = state.symbol
    config = state.config_json
    
    # 1. Get Data
    df = data_manager.get_data(symbol)
    if df.empty: return None

    # 2. Indicators
    # ... use vectorbt or pandas ...

    # 3. Logic
    # ...

    return {
        "direction": "BULLISH",
        "stop_loss": 100.0,
        "reason": "Test Signal"
    }
```
