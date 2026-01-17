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
1.  **Create Strategy Directory**
    *   Create a new directory: `services/strategy-core/app/strategies/<strategy_name>/`.
    *   Create `__init__.py` inside.

2.  **Implement Strategy Logic & Metadata**
    *   Create `services/strategy-core/app/strategies/<strategy_name>/strategy.py`.
    *   **Define `METADATA`** at the module level:
        ```python
        METADATA = {
            "name": "Strategy Name",
            "description": "Short description",
            "defaults": { "param": "value" }
        }
        ```
    *   Define the async function `async def strategy(state, params):` (Sync/Vectorized).
    *   **MUST** return `return entries, exits, signal_dict`.

3.  **Create Documentation (README.md)**
    *   Create `services/strategy-core/app/strategies/<strategy_name>/README.md`.
    *   **Content MUST include:**
        *   `# Strategy Name`
        *   `## Description`: High-level logic explanation.
        *   `## Formula`: Mathematical definition of triggers.
        *   `## Parameters`: List of config keys and defaults.
        *   `## AI Metadata`: Schema of the `metadata` field for AI Agents.

4.  **Add a Unit Test**
    *   Create a new test file: `services/strategy-core/tests/test_strategy_<name>.py`.
    *   Mock `data_manager` and `state`.
    *   Assert that the strategy returns the expected signal and **valid metadata**.
    *   **Run Tests via Docker:**
        ```bash
        docker compose exec strategy-core uv run pytest services/strategy-core/tests/test_strategy_<name>.py
        ```
    *   **(Optional)** Verify discovery by running `test_registry_discovery.py` if available.

5.  **Sync with Database (Frontend Visibility)**
    To make the strategy appear in the Frontend Editor ("Saved Strategies"), run the seed script:
        ```bash
        curl -X POST http://localhost:8000/api/v1/strategies/reload
        ```

6.  **Verify**:
    *   **Backtest**: Check Frontend -> Strategy Editor (Select Strategy).
    *   **Live**: Check Frontend -> Bot.


## Code Template
```python
import vectorbt as vbt
import pandas as pd

METADATA = {
    "name": "My Strategy",
    "description": "Description...",
    "defaults": { "period": 14 }
}

def strategy(data, params=None):
    """
    Unified Strategy Function (Sync/Vectorized)
    Args:
        data: pd.DataFrame (ohlcv)
        params: dict of parameters
    Returns:
        entries, exits, signal_dict
    """
    if params is None: params = {}
    period = int(params.get("period", METADATA["defaults"]["period"]))
    
    close = data['close']
    
    # 1. Calculate Indicators
    sma = vbt.MA.run(close, period)
    
    # 2. Generate Signals
    entries = sma.ma_crossed_above(close)
    exits = sma.ma_crossed_below(close)
    
    # 3. Return Protocol
    latest_signal = {
        "direction": "BULLISH" if entries.iloc[-1] else "BEARISH",
        "stop_loss": float(sma.ma.iloc[-1]),
        "reason": "MA Cross",
        "metadata": {
            "strategy_name": METADATA["name"],
            "description": METADATA["description"],
            "signal_timestamp": str(df.index[-1]),
            "rsi_val": 25.5,
            "confidence": 0.85
        }
    }
    
    return entries, exits, latest_signal
```
