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

## 2.5 Strategy Compositions

### STRAT_VOL_BREAKOUT_V1
A pure volatility expansion strategy.
1.  **Context**: Market is in `BLOCK_VOL_COMPRESSION`.
2.  **Trigger**: `BLOCK_VOL_BREAKOUT` confirmed.
3.  **Risk**: Stop Loss at `2.0 * ATR` from entry. Target at `1.0 * ADR`.
4.  **AI Metadata**: Must report `compression_ratio`, `regime`, `volatility_metrics`.

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

---

## 4. Layer 5: AI Coach Intervention
The AI Coach monitors the *execution behavior*, not the price.

1.  **Tilt Detection**:
    *   If `Time_Between_Trades < 5 min` AND `Last_Result == LOSS` -> Flag "Revenge Trading".
2.  **Lockout**:
    *   Execution Service returns `423 Locked (Psychological Stop)`.
3.  **Unlock**:
    *   User must complete `POST /coach/mental-history` to reset the lock.
