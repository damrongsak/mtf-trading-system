---
name: new-strategy-implementation
description: |
    Use this skill when you need to create, add, or implement an institutional-grade "World-Class" trading strategy in the `strategy-core` service.
---

# New Strategy Implementation (World-Class Standard v2.8)
**Goal:** Create a high-performance, learnable, and robust strategy in `services/strategy-core`.

## 🛡️ Mandates
1.  **Vectorization**: All strategies MUST be vectorized using `vectorbt` for O(1) backtesting.
2.  **Rich Metadata**: Signals MUST include a `logic_path` and `features` for AI learning.
3.  **Hierarchy**: Strategies MUST be linked to a `Fund` and `BrokerAccount` via the database.
4.  **Sync**: Local files MUST be synced to the DB using `seed_strategies.py` and `sync_strategy_deployments.py`.

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
*   **Define Rich Metadata**:
    Include `logic_path` (list of confluences) and `features` (raw indicator values) in the `signal_dict`.

### 3. Database Synchronization (MANDATORY)
Local changes are not live until synced. Run these commands from the root:
1.  **Sync Code to Template Store**:
    ```bash
    docker compose exec strategy-core python scripts/seed_strategies.py
    ```
2.  **Register as Deployment (Sandbox/Live)**:
    ```bash
    docker compose exec strategy-core python scripts/sync_strategy_deployments.py
    ```

### 4. Validation Gates
The strategy MUST pass these tests before deployment:
1.  **Monte Carlo**: Ruin Probability < 1% (use `scripts/monte_carlo_smc_atr.py` as reference).
2.  **Walk-Forward (WFA)**: Robustness Score > 60% via `app.proving_ground.validator`.
3.  **Minimax Regret**: Check `metadata.minimax_regret_score > 1.5`.

## Code Template (World-Class)
```python
import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Tuple, Dict, Any
from app.foundry.vector_base import VectorizedStrategyBase

METADATA = {
    "name": "World Class Strategy",
    "description": "High-performance learnable strategy",
    "defaults": { "period": 14, "threshold": 30 }
}

class MyWorldClassStrategy(VectorizedStrategyBase):
    def run_vector(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series]:
        p = {**METADATA["defaults"], **(params or {})}
        close = data['close']
        
        # 1. Vectorized Indicators
        rsi = vbt.RSI.run(close, window=p['period']).rsi
        
        # 2. Vectorized Signals
        entries = rsi < p['threshold']
        exits = rsi > 70
        
        return entries, exits

def strategy(data: pd.DataFrame, params: Dict[str, Any] = None):
    """Standard Entry Point"""
    obj = MyWorldClassStrategy("my_strat")
    entries, exits = obj.run_vector(data, params)
    
    # Build Rich Metadata for AI Analyst
    last_idx = -1
    signal_dict = {
        "direction": "BULLISH" if entries.iloc[last_idx] else "FLAT",
        "entry_price": float(data['close'].iloc[last_idx]),
        "logic_path": ["RSI_OVERSOLD"] if entries.iloc[last_idx] else [],
        "metadata": {
            "features": {
                "rsi_val": float(rsi.iloc[last_idx])
            }
        }
    }
    return entries, exits, signal_dict
```
