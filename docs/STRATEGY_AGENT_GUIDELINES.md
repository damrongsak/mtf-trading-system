# MTF Olympus: AI Strategy Agent Guidelines (v2.8)

This document serves as the foundational mandate for any AI Agent or developer working on the `strategy-core` service. Adherence to these standards ensures system stability, high-performance execution, and learnability for the AI Analyst.

## 1. Strategy Architecture & Hierarchy

### 1.1 The Deployment Chain
A strategy NEVER exists in isolation. It must always be resolved within the following hierarchy:
`User -> Fund -> BrokerAccount -> Strategy (Deployment)`

- **Fund:** Defines the NAV, Max Drawdown, and Global Risk Multiplier.
- **BrokerAccount:** The technical gateway (OANDA, cTrader, etc.) where orders are executed.
- **Strategy:** The logic unit. It must be linked to a `fund_id` and `broker_account_id` in the database to be "Live" or "Shadow".

### 1.4 Mandatory File Structure
Every strategy folder in `app/strategies/` MUST contain:
1.  **`strategy.py`**: The logic implementation.
2.  **`README.md`**: Standard documentation (Logic overview, parameter definitions, and timeframe requirements). 
    - *Note:* AI Agents MUST generate this file when creating a new strategy.

### 1.5 The "Olympus Standard" Audit (Quality Gates)
Strategies that fail these checks are considered "Legacy" and must be refactored:
- **NO Direct DB Access:** All data must be passed via the `data` argument in `run_vector`.
- **Unit Normalization:** MUST use `app.core.units.UnitConverter`. Zero ad-hoc multiplication/division for lots/units.
- **Rich Metadata:** Signal `metadata` MUST include a `logic_path` list for the AI Analyst.
- **Param Integrity:** `METADATA["defaults"]` MUST be complete. "Magic numbers" in code are forbidden.

### 1.3 Synchronization Mandate (Crucial)
Local code changes in the template directory (filesystem) ARE NOT automatically reflected in existing DB deployments until synced.
- **Mandatory Sync Steps:**
    1.  **Code Seeding:** Run `scripts/seed_strategies.py` to push the physical `strategy.py` content and its `defaults` parameters into the `saved_strategies` table.
        - *Advanced:* Use `--strategy <folder>` to sync a specific unit, or `--clear` to purge and rebuild the registry.
    2.  **Deployment Registration:** Run `scripts/sync_strategy_deployments.py` to ensure every template has a corresponding entry in the `strategies` table for live/shadow use.
- **Validation Rule:** Before any backtest or deployment, verify that `code_size` in the DB matches the local file size. AI Agents MUST ensure that `METADATA["defaults"]` align with `SavedStrategy.parameters` to prevent "Ghost Parameter" bugs.

## 2. Coding Standards for "World-Class" Strategies

### 2.1 Vectorization (Vectorbt) Mandate
Strategies must support high-speed backtesting.
- **Base Class:** Inherit from `app.foundry.vector_base.VectorizedStrategyBase`.
- **Method:** Implement `run_vector(data, params)`.
- **Return:** Must return boolean series/dataframes for entries and exits to allow $O(1)$ simulation.

### 2.2 Rich Metadata (The "Learnability" Rule)
Signals must not just say "BUY" or "SELL". They must provide the **"Why"** in a machine-readable format.
- **Mandatory Fields in `metadata`:**
    - **Indicator States:** Raw values of indicators used (e.g., `bb_lower`, `stoch_k`).
    - **Market Regime:** The detected market state (e.g., `TRENDING_UP`, `RANGING`).
    - **SMC Context:** Proximity to Order Blocks, FVG gaps, or Liquidity zones.
    - **Confidence Score:** Derived from confluences or Minimax Regret.

## 3. Strategy Lifecycle & Validation

### 3.1 Validation Gates
Before a strategy can move from `Sandbox` to `Live`, it must pass:
1.  **Local Unit Test (Pre-Seeding):** Every strategy MUST have a `tests/test_strategy_{name}.py` file. Run `pytest` locally to ensure signal generation with OHLCV data. **Admission into the DB (Seeding) is FORBIDDEN without passing tests.**
    - **AI Command:** `docker compose exec strategy-core pytest tests/test_strategy_{name}.py`
    - **Debug AI:** `docker compose exec strategy-core python3 tests/test_strategy_{name}.py` (to see raw `print` output).
2.  **Logic Test (API):** Functional signals generated in `Backtest API`.
3.  **Monte Carlo (Bootstrap):** Ruin Probability < 1% over 1000 simulations.
4.  **Walk-Forward (WFA):** Robustness Score > 60%.
5.  **Minimax Filter:** Regret score threshold check.

### 3.2 Sandbox Testing
- **Shadow Mode:** Use `is_active=True` and `is_shadow=True`.
- Signals are generated on live ticks and saved to `opportunity_log` and `signal_log`.
- NO orders are sent to the broker. This is the final gate before real capital risk.

## 4. AI Analyst Integration
The `metadata` dictionary in the signal is the primary data source for the **AI Analyst (Gemini 2.5)**. 
- Use descriptive keys (e.g., `distance_to_bullish_ob` instead of `dist_ob`).
- Include the "Logic Path" (e.g., `{"logic_path": ["BB_OVERSOLD", "STOCH_CROSS", "OB_REJECTION"]}`).

## 5. API Backtesting & Optimization Workflow
After seeding a strategy to the DB, use the API for large-scale validation.

### 5.1 Authentication (Service User)
- **Account:** `demo1` / `password123`
- **Flow:** `POST /api/v1/auth/login` -> Extract `access_token`.

### 5.2 Vectorized Backtest
- **Endpoint:** `POST /api/v1/backtest/run`
- **Body:**
```json
{
  "strategy_name": "quasimodo_v1",
  "symbol": "XAU_USD",
  "timeframe": "15min",
  "params": { "risk_pct": 0.01, "swing_strength": 2 },
  "range": { "start": "2024-01-01", "end": "2024-03-01" }
}
```

### 5.3 Multi-Param Optimization
- **Endpoint:** `POST /api/v1/optimize/run`
- **Body:**
```json
{
  "strategy_name": "quasimodo_v1",
  "param_space": {
    "swing_strength": [2, 3, 5],
    "ema_fast": [8, 13, 21]
  },
  "metric": "sharpe_ratio"
}
```

## 6. Olympus Extensions (Institutional Roadmap)
To achieve truly "World-Class" status, strategies should implement:
- **Correlation Guard:** Use `PortfolioService` to skip trades if existing exposure to correlated symbols is > 20%.
- **News Imbalance Filter:** Check `state_updates` (Redis) for high-impact News event proximity.
- **SMC Liquidity Checks:** Integrate `LiquidityAnalyzer` to confirm "Sweep" displacement volume.
- **Risk Parity:** Auto-adjust lot size based on Portfolio Volatility (PyPortfolioOpt).
- **AI Analyst Journaling:** Programmatically send every signal's `metadata` to the `ai-analyst` for psychological and strategic "Debunking" (Post-Trade Analysis).
- **Knowledge Graph (FalkorDB):** Store successful QM patterns as graph nodes to identify high-probability structural confluences across symbols.

---
*Last Updated: 2026-03-24*
