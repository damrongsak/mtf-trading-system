# MTF Olympus - Execution & Risk Logic
# Layer 2 (Structure) & Layer 4 (Risk)

## 1. Overview
This document defines the specialized logic for **Layer 2 (Strategy Foundry)** and **Layer 4 (Risk Citadel)**. Unlike the MVP which had one hardcoded strategy, Olympus uses standardized "Logic Blocks" and a Game-Theoretic Risk Engine.

---

## 2. Layer 2: Strategy Foundry (Logic Blocks)

Strategies are assembled from these standardized, reusable blocks.

### 2.1 Trend Blocks (The "Bias")
* Used to determine the overall market direction.
* **BLOCK_TREND_EMA_CROSS**:
    * **Logic**: Price > EMA(Period).
    * **State**: BULLISH if Close > EMA, BEARISH if Close < EMA.
* **BLOCK_TREND_AMA**:
    * **Logic**: Kaufman's Adaptive Moving Average slope.
    * **State**: BULLISH if AMA is rising, BEARISH if falling.

### 2.2 Structure Blocks (The "Where")
* Used to identify High-Probability Zones (POI).
* **BLOCK_STRUCT_SMC_OB**:
    * **Logic**: Order Blocks (Last opposing candle before displacement).
    * **State**: VALID if Price is inside the OB body range.
* **BLOCK_STRUCT_FIB_GOLDEN**:
    * **Logic**: Fibonacci Retracement (0.5 - 0.618) of the last swing.
    * **State**: VALID if Price is inside the Golden Pocket.
* **BLOCK_STRUCT_LIQUIDITY_MATRIX** (Hunter Mode):
    * **Logic**: Tracking resting orders and session extremes.
    * **Fields**: `asian_range`, `pdh_pdl`, `equal_high_low`, `psych_levels`.
    * **State**: RAID_IN_PROGRESS if price pierces level. CONFIRMED_SWEEP if followed by V-rejection.

### 2.3 Momentum/Trigger Blocks (The "When")
* Used to time the entry with precision.
* **BLOCK_MOM_RSI_CROSS**:
    * **Logic**: RSI(14) crosses 50 or exits oversold/overbought.
* **BLOCK_MOM_VECTOR_CANDLE**:
    * **Logic**: 15m Candle with `Body/Range > 0.70` (SMC Impulse).
    * **State**: TRIGGER if confirmed close.

### 2.4 Volatility Blocks (New)
* Used to identify compression and expansion regimes.
* **BLOCK_VOL_COMPRESSION**:
    * **Logic**: `ATR(14) < SMA(ATR(14), 20)` OR `Current_Daily_Range < ADR(20)`.
    * **State**: COMPRESSION if true.
* **BLOCK_VOL_BREAKOUT**:
    * **Logic**: Price Close > Upper Keltner Channel OR < Lower Keltner Channel.
    * **State**: BREAKOUT_UP / BREAKOUT_DOWN.

### 2.5 Liquidity & Gamma Analysis (v2.5)
* **Gamma Flip Calculation (OIWAP)**:
    * **Logic**: Instead of finding the strike with the absolute minimum `|Call - Put|` (which fails on sparse/zero-OI data), the system uses an **OI-Weighted Average Price (OIWAP)**.
    * **Formula**: `Flip_Level = Σ(Strike_i * Total_OI_i) / Σ(Total_OI_i)` for all `Total_OI_i > 0`.
    * **Benefit**: Anchors the "Zero Gamma" level to the actual center of gravity of institutional positioning.
* **GEX V2.5 Integrity Standards**:
    * **Reality-Anchoring**: The `underlying_price` from option symbols must match the `current_spot_price` within ±20%. Non-compliance triggers `STALE_OR_SCALE_DIVERGENCE`.
    * **Noise Floor Guard**: Total GEX across the analysis snapshots must be >= 1.0 to ensure a statistically significant sample.
    * **Proximity Guard**: Rejects Gamma Flip levels if they are > 25% away from Spot (Impossible Gamma Flips).
    * **Timeframe Alignment**: Default institutional aggregation is **90 Days (Quarterly)**.

## 2.6 Strategy Compositions

### STRAT_VOL_BREAKOUT_V1
A pure volatility expansion strategy.
1.  **Context**: Market is in `BLOCK_VOL_COMPRESSION`.
2.  **Trigger**: `BLOCK_VOL_BREAKOUT` confirmed.
3.  **Risk**: Stop Loss at `2.0 * ATR` from entry. Target at `1.0 * ADR`.
4.  **AI Metadata**: Must report `compression_ratio`, `regime`, `volatility_metrics`.

### STRAT_SMC_HUNTER_V1
A liquidity raid strategy (Phase 64).
1.  **Context**: `BLOCK_VOL_COMPRESSION` OR `RANGING`.
2.  **Prerequisite**: `RAID_IN_PROGRESS` on Asian Range or EQH/EQL.
3.  **Trigger**: `CONFIRMED_SWEEP` (V-Shape rejection back into the range).
4.  **Risk**: Stop Loss at Raid High/Low. Target at opposite Liquidity Pool.
5.  **Logic**: "Wait for others to be stopped out before considering entering."

---

## 3. Layer 4: Risk Citadel (The Rules)

These rules are enforced by the `Execution Service` **before** any trade is submitted to the broker.

### 3.1 Minimax Regret Engine (The "Kernel")
**Goal**: Minimize the maximum possible regret (loss of capital or missed opportunity).

1.  **Inputs**:
    *   `Signal Confidence` (0.0 - 1.0)
    *   `Market Volatility` (ATR Regime)
    *   `Strategy Drawdown` (Current DD%)
2.  **Regret Matrix Calculation**:
    *   *Regret(Trade)* = Potential Loss if Trade Fails.
    *   *Regret(NoTrade)* = Potential Missed Profit if Trade Wins.
    *   *Worst Case*: `Max(Regret(Trade), Regret(NoTrade))`.
3.  **Decision**:
    *   If `Worst Case > User_Pain_Threshold`, **REJECT** trade.
    *   *Example*: If User cannot handle a $50 loss (Pain Threshold), and the setup implies a $60 risk for a low-probability win, Minimax rejects it.

### 3.2 Portfolio Risk Parity (Allocation)
**Goal**: Equalize risk contribution across symbols in a portfolio to prevent over-exposure to highly volatile assets.

1.  **Inverse Volatility (ERC)**:
    *   `Weight_i = (1 / Volatility_i) / Sum(1 / Volatility_j)`
2.  **Hierarchical Risk Parity (HRP)**:
    *   Preferred for multi-asset portfolios. Uses tree-clustering to handle correlations without inverting a covariance matrix.
3.  **Effect**:
    *   High-Volatility strategies get smaller position sizes.
    *   Low-Volatility strategies get larger position sizes.
4.  **Constraint**:
    *   Total Risk across all active trades must not exceed `Fund_Max_Risk` (e.g., 2% of equity).
    *   Dynamic sizing: `Units = (Equity * Risk% * Weight_i) / StopLoss_Distance`.

### 3.3 The Smart Constraints (Hierarchical Risk)
These rules are dynamically enforced by the `Execution Service` via database configurations (`Fund`, `BrokerAccount`):

1.  **Hierarchical Limit**: Risk is capped by `Min(Fund.max_risk, Account.max_risk)`.
    *   *Default*: **$10** (Configurable in DB, not hardcoded).
2.  **Dynamic Position Sizing**: Optional `Risk = NAV * Fund.risk_percentage`.
    *   Hard Cap: Still constrained by the Hierarchical Limit.
3.  **Min Lot Size**: Trades leading to lots < **0.01** (or broker min) are rejected.
4.  **Volatility Guard**: If ATR > 100 pips (Flash Crash mode), trading is suspended.
5.  **Momentum Displacement Limit**: Rejects `liquidity_sweep` signals if $V_d > 3\sigma$ (where $V_d$ is displacement velocity over 5 periods).
6.  **Volume Delta Confirmation**: Sweeps MUST be accompanied by "Aggressive Absorption" (positive volume delta for bullish, negative for bearish).
7.  **Macro Volatility Trigger**: If VIX or GVZ exceeds the 95th percentile threshold (e.g., VIX > 35), leverage is automatically reduced to 25% of the fund limit.

### 3.4 Hierarchical Citadel Filters (Phase 28+)
The following filters operate on a Bottom-Up validation hierarchy (Strategy -> BrokerAccount -> Fund -> System). They are dynamically configured in the `risk_filters` table.

**Validation Flow**:
1.  **Phase 1 (Core Order Validators)**:
    *   `SL_MANDATORY`: Rejects if `sl_price <= 0`.
    *   `TP_MANDATORY`: Rejects if `tp_price <= 0`.
    *   `SL_DISTANCE`: Rejects if SL is too close (e.g. `min_pip_distance`: 10).
    *   `RR_RATIO`: Rejects if Reward:Risk < minimum (e.g. `min_ratio`: 1.0).
2.  **Phase 2 (Market Condition Filters)**:
    *   `NEWS_FILTER`: Blocks around High Impact events (e.g. `minutes_before`: 30, `minutes_after`: 30).
    *   `SESSION_FILTER`: Blocks specific time windows (e.g. London Open volatility spike).
    *   `VOLATILITY_FILTER`: Minimum/Maximum ATR requirements.
    *   `SPREAD_FILTER`: Rejects if real-time spread > `max_pips`.
3.  **Phase 3 (Risk Limit Filters)**:
    *   `MAX_DAILY_DRAWDOWN`: Pauses trading if daily realized+unrealized loss > threshold.
    *   `MAX_ORDERS_PER_DAY`: Caps the total number of trades per target.
    *   `CONSECUTIVE_LOSSES`: Auto-pauses target if X consecutive losses occur.

If any tier (Strategy, BrokerAccount, Fund) fails a filter, the order is **REJECTED**.

### 3.5 Institutional Resilience & Stability (Phase 29+)
To ensure survival during extreme market events (Flash Crashes, News Spikes), the following professional-grade protections are enforced:

1.  **Global Kill Switch**:
    *   **Logic**: Monitoring `system:kill_switch` in Redis.
    *   **Effect**: If `1`, all `OPEN` requests are immediately rejected. `CLOSE/MODIFY/CANCEL` may be processed with warnings to ensure risk management.
2.  **Priority Request Queueing**:
    *   **Logic**: Multiple Redis queues sorted by urgency.
    *   **Priority Queue (`queue:execution:priority`)**: For Close, Modify, TRSL, and SL/TP updates.
    *   **Default Queue (`queue:execution:commands`)**: For Open and non-critical requests.
3.  **Broker Circuit Breaker**:
    *   **Logic**: Tracks consecutive API/Connection failures.
    *   **Effect**: If failures > 5, enters a 30s Cooldown. All requests during cooldown are rejected locally to prevent broker rate-limiting or log flooding.
4.  **Adaptive Tick Throttling**:
    *   **Logic**: Capping WebSocket broadcast frequency.
    *   **Interval**: 100ms (10Hz).
    *   **Target**: Dashboard and API buffers (internal strategy streams remain native).
5.  **Multi-Timeframe Timeout**:
    *   **Logic**: `asyncio.wait_for` on all broker I/O.
    *   **Duration**: 15s (Standard) to 30s (Account Summary).
6.  **Rule 7 (DB-Free Hot Path)**:
    *   **Policy**: Proactive database writes are FORBIDDEN in the execution hot path.
    *   **Constraint**: Internal processing latency target < 10ms.
    *   **Enforcement**: Use Redis Streams for fill persistence.

### 3.6 Broker Credential Verification (Demo/Activation Fix)
To prevent "dead" accounts and ensure immediate demo activation, the system enforces broker-side validation during account creation:
1.  **Validation Path**: `API Gateway` -> `Data Pipeline` (`/api/v1/discovery/symbols`).
2.  **Required Fields**: `client_id`, `client_secret`, `token`, and `account_id` (cTrader/ICMarkets).
3.  **Automatic Sync**: `account_number` is automatically synced to `credentials["account_id"]` if missing.
4.  **Enforcement**: Accounts with invalid credentials will be rejected with `HTTP 400 Bad Request` and a descriptive error from the broker.

### 3.7 HFT-lite Startup & Warm-up Protocols
To ensure the "Execution Edge" is ready for sub-50ms processing from the first signal, the `Execution Service` implements a graduated startup sequence:
1.  **Dependency Verification**: MUST verify Redis and PostgreSQL connectivity before binding the API port.
2.  **L3 Cache Warm-up**: Background task (`_warmup_execution_cache`) MUST pre-hydrate active accounts, credentials, and funds into L1 (Memory) and L2 (Redis).
3.  **Symbol Hydration**: Adapters MUST pre-populate symbol/contract ID maps. If a cache miss occurs, the service MUST call the `Data Pipeline` directly (Direct Service Call) to avoid circular dependencies with the `API Gateway`.
4.  **Health Resilience**: Infrastructure (`docker-compose.yml`) MUST allow at least 60s for the warm-up sequence via extended health check retries (10x 10s) and a `start_period` of 30s.

---

### 3.8 Persistence & Data Integrity (v3.3)
To ensure 100% data fidelity between the Execution Service worker, the Sync Service, and the API Gateway, the following persistence rules are mandatory:

1.  **Rule: Absolute Pricing**: 
    - **Logic**: All commodity (e.g., XAU/USD) and Forex prices MUST be stored as **absolute prices** (e.g., 4654.17) in the trades table. 
    - **Constraint**: Relative pips, pipettes, or cent-scaled values are forbidden for database persistence as they lead to cross-broker scaling errors.
2.  **Rule: Deterministic UUID Reconciliation**:
    - **Logic**: Cross-service trade_id generation MUST use uuid.uuid5(uuid.NAMESPACE_DNS, f"{account_id}_{broker_order_id}").
    - **Benefit**: This allows the background worker to perform a db.merge() on "Ghost trades" created by the Sync Service, seamlessly updating them with SL/TP and strategy metadata without unique constraint violations.
3.  **Rule: Standardized Lot Scaling**:
    - **Logic**: Broker-provided raw units MUST be scaled to standard lots using a **100,000.0** divisor (e.g., 1000 units = 0.01 lots).
    - **Enforcement**: This divisor is consistent across the adapter (ctrader.py), the background worker (worker.py), and the sync service (sync_service.py).

---

## 3.10 Directionality & Unit Sign Standard (v2.1)

To eliminate "sign-flip" errors and ensure cross-broker protocol safety, MTF Olympus enforces the following directionality standard:

1.  **Rule: Strictly Positive Units**: All internal transmission and storage of volume MUST use absolute values (strictly positive).
2.  **Rule: Explicit Side Parameter**: Order placement methods MUST accept a `side` parameter (`BUY` or `SELL`) to determine trade direction.
3.  **Mapping Rules**:
    - **Strategy-Core**: Maps `BULLISH` -> `BUY` and `BEARISH` -> `SELL`.
    - **API Gateway**: Removes any legacy unit-signing logic; passes absolute units and explicit side.
    - **Execution Service**: Rejects any order where `units <= 0`.
    - **Adapters**: The final unit sign (if required by broker API like OANDA) is applied *only* at the adapter's edge.

---

## 4. Layer 5: AI Coach Intervention
The AI Coach monitors the *execution behavior*, not the price.

1.  **Tilt Detection**:
    *   If `Time_Between_Trades < 5 min` AND `Last_Result == LOSS` -> Flag "Revenge Trading".
2.  **Lockout**:
    *   Execution Service returns `423 Locked (Psychological Stop)`.
3.  **Unlock**:
    ---

## 3.9 Knowledge-Driven Intelligence (v2.3)
Bridging the Knowledge Graph (FalkorDB) with Execution & Risk layers.

### 3.9.1 Semantic Risk Multiplier (Km)
The Execution Service calculates a **Km** based on the signal's `knowledge_context`.

1. **Km = 1.0 (Neutral)**: No conflicting or supporting knowledge found.
2. **Km = 1.25 - 1.5 (Confirmed)**: High alignment with Geopolitical bias or War Premium (e.g., Long Gold confirmed by Central Bank demand node).
3. **Km = 0.5 - 0.75 (Conflict)**: Direction contradicts Graph context (e.g., Long Gold while the Graph shows an "End of High Inflation" node).
4. **Final Lot Size** = `Original_Lot * Km`.

### 3.9.2 Intelligent Signal Filtering
Rules for rejecting signals based on Knowledge context:
1. **Rule [K1]**: Reject any "High Risk" signal if Knowledge Graph identifies an active "Market Closed" or "Holiday" node for the asset.
2. **Rule [K2]**: Flag as "LOW_CONFIDENCE" if the signal's `confidence` > 0.8 but `knowledge_score` < 0.70.
