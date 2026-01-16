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

2.  **Create Strategy Directory**
    *   Create a new directory: `services/strategy-core/app/strategies/<strategy_name>/`.
    *   Create `__init__.py` inside.

3.  **Implement Strategy Logic**
    *   Create `services/strategy-core/app/strategies/<strategy_name>/strategy.py`.
    *   Define the async function `async def strategy(state, data_manager):`.
    *   **MUST** return a dict with keys: `direction` ("BULLISH"/"BEARISH"), `stop_loss`, `reason`, and **`metadata`**.
    *   **MUST** populate `metadata` with structured data.

4.  **Create Documentation (README.md)**
    *   Create `services/strategy-core/app/strategies/<strategy_name>/README.md`.
    *   **Content MUST include:**
        *   `# Strategy Name`
        *   `## Description`: High-level logic explanation.
        *   `## Formula`: Mathematical definition of triggers.
        *   `## Parameters`: List of config keys and defaults.
        *   `## AI Metadata`: Schema of the `metadata` field for AI Agents.

5.  **Register the Strategy**
    *   Import the function in `services/strategy-core/app/registry.py`:
        `from app.strategies.<strategy_name>.strategy import strategy as <name>_strategy`
    *   Add to `StrategyRegistry._strategies`.

6.  **Add a Unit Test**
    *   Create a new test file: `services/strategy-core/tests/test_strategy_<name>.py`.
    *   Mock `data_manager` and `state`.
    *   Assert that the strategy returns the expected signal and **valid metadata**.
    *   **Run Tests via Docker:**
        ```bash
        docker compose exec strategy-core uv run pytest services/strategy-core/tests/test_strategy_<name>.py
        ```

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
        "reason": "Test Signal",
        "metadata": {
            "signal_timestamp": str(df.index[-1]), # Explicit candle time
            "rsi_val": 25.5,
            "ema_trend": "UP",
            "confidence": 0.85
        }
    }
```
