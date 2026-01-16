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
    *   Define the async function `async def strategy(state, data_manager):`.
    *   **MUST** return a dict with keys: `direction` ("LONG"/"SHORT"), `stop_loss`, `reason`, and **`metadata`**.

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

## Code Template
```python
METADATA = {
    "name": "My Strategy",
    "description": "Description...",
    "defaults": { "period": 14 }
}

async def strategy(state, data_manager):
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
        "direction": "LONG", # or "SHORT"
        "stop_loss": 100.0,
        "take_profit": 110.0,
        "reason": "Test Signal",
        "metadata": {
            "strategy_name": METADATA["name"],
            "description": METADATA["description"],
            "signal_timestamp": str(df.index[-1]),
            "rsi_val": 25.5,
            "confidence": 0.85
        }
    }
```
