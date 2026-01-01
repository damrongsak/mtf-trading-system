This document serves as the **Product Requirements Document (PRD.md)** for the **MTF Olympus** platform (v2.0), enabling the transition from a single-user trading bot to a distributed quant hedge fund platform.

This PRD defines the **What** and **Why** of the product; the **How** (architecture, API contracts, technical implementation) is detailed in the corresponding SDD files in the `/specs` directory.

---

# PRD.md: MTF Olympus Planform (v2.0)

| Key Detail | Value |
| :--- | :--- |
| **Product Name** | MTF Olympus (Formerly Phoenix) |
| **Document Version** | 2.0 (Olympus Enhancement) |
| **Target Audience** | Retail Quants, Fund Managers, AI Engineers |
| **Release Target** | Phase 2 Completion (Distributed Quant Platform) |
| **Status** | **In Development** |

---

## 1. Overview & Vision

### 1.1. Price Drift Problem
Retail trading platforms (and bots) fail because they sell "Signals" (Fish) instead of "Logic" (Fishing Rods). They suffer from:
1.  **Curve Fitting**: Strategies look good in backtests but fail in live markets.
2.  **Gambler’s Ruin**: Lack of portfolio-level risk management.
3.  **Psychological Decay**: No mechanism to fix the human error (Tilt/Fear).

### 1.2. Product Vision
**MTF Olympus** is an **Operating System (OS)** for wealth creation. It democratizes the sophisticated tools used by institutional hedge funds—**Game Theoretic Risk Management**, **Walk-Forward Validation**, and **AI-Driven Psychology Coaching**—allowing individuals to act as their own Quant Fund Managers.

### 1.3. The 5 Pillars of Olympus
The platform is built on five functional pillars:
1.  **The Strategy Foundry**: Standardized "Lego Blocks" for creating strategies (no ad-hoc code).
2.  **The Proving Ground**: rigorous Walk-Forward Validation to prevent overfitting.
3.  **The Risk Citadel**: Minimax Regret & Portfolio Risk Parity engine.
4.  **The Execution Edge**: Smart Order Routing and Liquidity analysis.
5.  **The AI Coach**: Psychological intervention via Mental Hand History.

---

## 2. Goals and Success Metrics

| ID | Goal | Success Metric (KPI) |
| :--- | :--- | :--- |
| **G1** | **Minimize Regret** | Zero trades accepted where potential "Regret" (Max Drawdown contribution) exceeds user threshold. |
| **G2** | **Robustness** | Strategies must pass "Walk-Forward Gauntlet" (Train/Test deviation < 20%) to be verified. |
| **G3** | **Capital Preservation** | Portfolio Risk Parity ensures no single strategy contributes > X% to total risk. |
| **G4** | **Psychological Correction** | AI Coach successfully detects "C-Game" (Tilt) and forces "Mental Hand History" completion. |
| **G5** | **Community Alpha** | Successful sharing of `StrategyConfig.json` between users via Marketplace. |

---

## 3. Target Users

| User Type | Profile | Core Need Solved |
| :--- | :--- | :--- |
| **The Architect (Quant)** | Designs logic. | **Foundry**: Rapidly assemble and validate logic without writing boilerplate code. |
| **The Fund Manager** | Allocates capital. | **Citadel**: Manage a portfolio of strategies with Risk Parity. |
| **The Trader** | Executes & monitors. | **AI Coach**: Keeps them in "A-Game" and prevents emotional tilt. |

---

## 4. Quantitative Standards (CFA & ML Alignment)
- **Core Metrics**: System MUST calculate Sharpe, Sortino, Max Drawdown, Alpha, and Beta using a centralized, validated engine.
- **Benchmarking**: Strategies MUST be benchmarked against relevant assets (e.g., Gold, Bitcoin) to prove Alpha.
- **Data Integrity**: Signal generation MUST use strictly bias-free data (e.g., Last Completed Candle `iloc[-2]`) to ensure valid ML training sets.
- **ML Readiness**: All metric calculations MUST be vectorized for performance.

## 5. Functional Requirements (Olympus v2.0)

### 4.1. The Strategy Foundry (Standardization)
| Requirement | Description (Behavior) |
| :--- | :--- |
| **F1.1** | Strategies must be defined as JSON configurations (`StrategyConfig`) referencing standardized Logic Blocks (Trend, MeanRev, etc.). |
| **F1.2** | The system must support "Assembler" logic to compile JSON configs into executable Python pipelines. |

### 4.2. The Proving Ground (Validation)
| Requirement | Description (Behavior) |
| :--- | :--- |
| **F2.1** | The system must enforce a "Walk-Forward Gauntlet" (Train on Period A, Test on Period B) for all strategies. |
| **F2.2** | Strategies must achieve a **Robustness Score > 80** to be marked as "Verified". |

### 4.3. The Risk Citadel (Minimax & Parity)
| Requirement | Description (Behavior) |
| :--- | :--- |
| **F3.1** | **Minimax Regret**: Before every trade, calculate worst-case outcome. Reject if it exceeds `pain_threshold`. |
| **F3.2** | **Risk Parity**: Dynamically allocate position sizes so that High-Vol and Low-Vol strategies contribute equal risk. |
| **F3.3** | **Dynamic Risk**: Position sizing is strictly determined by Risk Parity (Inverse Volatility). No hard dollar caps. |

### 4.4. The AI Coach (Psychology)
| Requirement | Description (Behavior) |
| :--- | :--- |
| **F4.1** | **State Detection**: Classify user state as A-Game, B-Game, or C-Game based on behavior (Loss Streak, rapid firing). |
| **F4.2** | **Intervention**: If C-Game is detected, lock execution and prompt for "Mental Hand History". |
| **F4.3** | **Coaching**: AI (Gemini) uses Steenbarger-style prompts to guide the user back to logic. |

### 4.5. The Alpha Marketplace
| Requirement | Description (Behavior) |
| :--- | :--- |
| **F5.1** | Users can publish `StrategyConfig.json` to the Marketplace (if Verified). |
| **F5.2** | Other users can "Clone" strategies to their local Foundry. |

---

## 5. Release Criteria (Phase 2)
1.  **[Foundry]** User can create a strategy via JSON and backtest it.
2.  **[Citadel]** Minimax Engine rejects at least one "technically valid" but "risk-heavy" trade in testing.
3.  **[Coach]** AI Coach successfully intervenes during a simulated "Tilt" session.
4.  **[Schema]** Database fully migrated to v2.0 Schema.