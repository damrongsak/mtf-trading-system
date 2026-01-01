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
**Goal**: Equalize risk contribution across strategies.

1.  **Formula**:
    *   `Weight_i = (1 / Volatility_i) / Sum(1 / Volatility_j)`
2.  **Effect**:
    *   High-Volatility strategies get smaller position sizes.
    *   Low-Volatility strategies get larger position sizes.
3.  **Constraint**:
    *   Total Risk across all active trades must not exceed `Fund_Max_Risk` (e.g., 2% of equity).

### 3.3 The Iron Guardrails (Hard Constraints)
These legacy rules remain as a final safety net:

1.  **Max Risk Cap**: No single trade can risk > **$10 USD** (or configured limit).
2.  **Min Lot Size**: Trades leading to lots < **0.01** are rejected.
3.  **Volatility Guard**: If ATR > 100 pips (Flash Crash mode), trading is suspended.

---

## 4. Layer 5: AI Coach Intervention
The AI Coach monitors the *execution behavior*, not the price.

1.  **Tilt Detection**:
    *   If `Time_Between_Trades < 5 min` AND `Last_Result == LOSS` -> Flag "Revenge Trading".
2.  **Lockout**:
    *   Execution Service returns `423 Locked (Psychological Stop)`.
3.  **Unlock**:
    *   User must complete `POST /coach/mental-history` to reset the lock.
