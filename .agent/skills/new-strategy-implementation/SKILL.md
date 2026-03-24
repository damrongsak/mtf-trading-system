---
name: new-strategy-implementation
description: |
    Use this skill when you need to create, add, or implement an institutional-grade "World-Class" trading strategy in the `strategy-core` service.
---

# New Strategy Implementation (World-Class Standard v2.9)
**Goal:** Create a high-performance, learnable, and robust strategy in `services/strategy-core` compliant with institutional professionalization.

## 🛡️ Mandates
1.  **Vectorization**: All strategies MUST be vectorized using `vectorbt` for O(1) backtesting.
2.  **Mandatory Traceability**: Signals MUST include a `reason` field (string) in the `signal_dict` explaining the logic (even if NEUTRAL).
3.  **Strategic Observability**: calculation-level logs MUST be captured in the `logs` list for API retrieval.
4.  **Sandbox Professionals**: Python sandbox strategies MUST use `pd`, `np`, `vbt`, `datetime`, `json`, and `time` natively (injected in scope).
5.  **Import Standard**: Use `import datetime` (module level) instead of `from datetime import datetime` to avoid shadowing.
6.  **Hierarchy**: Strategies MUST be linked to a `Fund` via the database.

## Process

### 1. Create Strategy Directory
*   Create a new directory: `services/strategy-core/app/strategies/<strategy_name>/`.
*   Create `__init__.py` and `README.md` inside.

### 2. Implement World-Class Logic
*   Create `services/strategy-core/app/strategies/<strategy_name>/strategy.py`.
*   **Inherit from `VectorizedStrategyBase`**:
    ```python
    from app.foundry.vector_base import VectorizedStrategyBase
    
    class MyStrategy(VectorizedStrategyBase):
        def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
            # Vectorized logic here returning boolean series
            ...
    ```
*   **Implement Professional Signal Dict**:
    ```python
    signal_dict = {
        "direction": "BULLISH",
        "reason": "Price > EMA200 and RSI < 30", # MANDATORY
        "logic_path": ["EMA_FILTER", "RSI_OVERSOLD"]
    }
    ```

### 3. Deployment & Instantiation
Institutional systems use the on-demand flow:
1.  **Sync Template**: Run `docker compose exec strategy-core python scripts/seed_strategies.py`.
2.  **Instantiate via API**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/strategies/instantiate \
      -H "Authorization: Bearer <token>" \
      -d '{"template_id": "your_strategy_v1", "fund_id": "...", ...}'
    ```

### 4. Validation Gates
The strategy MUST pass these tests before deployment:
1.  **Monte Carlo**: Ruin Probability < 1%.
2.  **Walk-Forward (WFA)**: Robustness Score > 60%.
3.  **Traceability Audit**: Ensure `reason` is present in manual tick response.

## Code Template (Institutional v2.9)
```python
import pandas as pd
import numpy as np
import vectorbt as vbt
import datetime # PREFERRED
from typing import Tuple, Dict, Any
from app.foundry.vector_base import VectorizedStrategyBase

METADATA = {
    "name": "Institutional RSI V1",
    "description": "Professional RSI with mandatory traceability",
    "defaults": { "period": 14, "threshold": 30 }
}

class InstitutionalRsi(VectorizedStrategyBase):
    def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
        p = {**METADATA["defaults"], **(params or {})}
        close = data['close']
        rsi = vbt.RSI.run(close, window=p['period']).rsi
        entries = rsi < p['threshold']
        exits = rsi > 70
        return entries, exits

def strategy(data: pd.DataFrame, params: Dict[str, Any] = None):
    obj = InstitutionalRsi("inst_rsi")
    entries, exits = obj.run_vector(data, params)
    
    last_idx = -1
    is_buy = entries.iloc[last_idx]
    
    # TRACEABILITY: Professional reasoning
    reason = "Price is neutral; waiting for oversold RSI"
    if is_buy:
        reason = f"RSI({data['close'].iloc[last_idx]:.2f}) is oversold below {params.get('threshold', 30)}"

    signal_dict = {
        "direction": "BULLISH" if is_buy else "FLAT",
        "reason": reason, # MANDATORY
        "logic_path": ["RSI_OVERSOLD"] if is_buy else [],
        "metadata": {"features": {"rsi": float(data['close'].iloc[last_idx])}}
    }
    return entries, exits, signal_dict
```
