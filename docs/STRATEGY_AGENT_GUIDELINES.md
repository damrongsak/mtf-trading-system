# MTF Olympus: AI Strategy Agent Guidelines (v2.8)

This document serves as the foundational mandate for any AI Agent or developer working on the `strategy-core` service. Adherence to these standards ensures system stability, high-performance execution, and learnability for the AI Analyst.

## 1. Strategy Architecture & Hierarchy

### 1.1 The Deployment Chain
A strategy NEVER exists in isolation. It must always be resolved within the following hierarchy:
`User -> Fund -> BrokerAccount -> Strategy (Deployment)`

- **Fund:** Defines the NAV, Max Drawdown, and Global Risk Multiplier.
- **BrokerAccount:** The technical gateway (OANDA, cTrader, etc.) where orders are executed.
- **Strategy:** The logic unit. It must be linked to a `fund_id` and `broker_account_id` in the database to be "Live" or "Shadow".

### 1.2 Two-Tier System
- **Templates (File-based):** Located in `app/strategies/{template_name}/strategy.py`. Pure logic.
- **Deployments (DB-based):** Records in the `strategies` table. Stores specific parameter overrides (`config_json`) and state (`is_active`, `is_shadow`).

### 1.3 Synchronization Mandate (Crucial)
Local code changes in the template folder ARE NOT automatically reflected in existing DB deployments until synced.
- **Mandatory Sync Steps:**
    1.  **Code Seeding:** Run `scripts/seed_strategies.py` to push the physical `strategy.py` content into the `saved_strategies` table (used for versioning and logic tracking).
    2.  **Deployment Registration:** Run `scripts/sync_strategy_deployments.py` to ensure every folder has a corresponding entry in the `strategies` table for sandbox/live use.
- **Validation Rule:** Before any backtest or deployment, verify that `code_size` in the DB matches the local file size. AI Agents must check `saved_strategies.code` consistency.

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
1.  **Logic Test:** Functional signals generated in `Backtest API`.
2.  **Monte Carlo (Bootstrap):** Ruin Probability < 1% over 1000 simulations.
3.  **Walk-Forward (WFA):** Robustness Score > 60% (Out-of-sample consistency).
4.  **Minimax Filter:** Regret score must exceed the threshold (default 1.5).

### 3.2 Sandbox Testing
- **Shadow Mode:** Use `is_active=True` and `is_shadow=True`.
- Signals are generated on live ticks and saved to `opportunity_log` and `signal_log`.
- NO orders are sent to the broker. This is the final gate before real capital risk.

## 4. AI Analyst Integration
The `metadata` dictionary in the signal is the primary data source for the **AI Analyst (Gemini 2.5)**. 
- Use descriptive keys (e.g., `distance_to_bullish_ob` instead of `dist_ob`).
- Include the "Logic Path" (e.g., `{"logic_path": ["BB_OVERSOLD", "STOCH_CROSS", "OB_REJECTION"]}`).

---
*Last Updated: 2026-03-20*
