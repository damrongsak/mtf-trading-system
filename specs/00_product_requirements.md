This document serves as the **Product Requirements Document (PRD.md)** for the initial release (MVP) of the MTF Trading System, focusing strictly on the core, risk-mitigating functionality as required by the Spec Driven Development (SDD) process.

This PRD defines the **What** and **Why** of the product; the **How** (architecture, API contracts, technical implementation) is detailed in the corresponding SDD files in the `/specs` directory.

---

# PRD.md: XAU/USD MTF Trading System (MVP: Risk-Controlled Core)

| Key Detail | Value |
| :--- | :--- |
| **Product Name** | XAU/USD MTF Alpha Engine (Codename: *Phoenix*) |
| **Document Version** | 2.0 (Expansion Phase) |
| **Target Audience** | Quant Funds, Prop Firms, Individual Traders |
| **Release Target** | Phase 2 Completion (Multi-Tenancy, Multi-Strategy, Oanda) |
| **Status** | In Progress |

---

## 1. Overview & Vision

### 1.1. Problem Statement

Automated trading systems often fail due to undisciplined risk management, look-ahead bias in testing, and a lack of confluence filtering, leading to rapid capital depletion, especially in high-volatility assets like XAU/USD (Gold) on small starting capital.

### 1.2. Product Vision

To build a robust, reproducible, and capital-preserving XAU/USD algorithmic trading system that integrates proven Smart Money Concepts (SMC) and Multi-Timeframe (MTF) analysis, enforced by a non-negotiable risk engine, allowing the trader to focus on system optimization and strategic enhancement rather than manual execution or emotional risk.

### 1.3. Expansion Scope Focus
The **Expansion Focus** is on **Multi-tenancy, Multi-Strategy, and Oanda Integration**. The system will support multiple users/funds, concurrent execution of diverse strategies, and live data ingestion from Oanda.

---

## 2. Goals and Success Metrics (MVP)

| ID | Goal | Success Metric (KPI) |
| :--- | :--- | :--- |
| **G1** | **Capital Preservation** (Highest Priority) | Zero instances of trades where the per-trade risk exceeds the defined limit per fund/strategy. |
| **G2** | **Strategy Validation** | Vectorized backtest (Vectorbt) yields a Sharpe Ratio > 0.8 and Max Drawdown < 15% across a 3-year historical period. |
| **G3** | **Multi-Tenancy** | Support for multiple users and funds with distinct roles (Owner, Trader, Viewer). |
| **G4** | **Multi-Strategy** | Concurrent execution of at least 3 distinct strategies with independent state management. |
| **G5** | **Data Integration** | Successful ingestion and processing of live market data from Oanda v20 API. |
| **G6** | **Trading Journal** | Structured psychological journal capturing mental patterns, game levels, and root cause analysis for AI-driven performance improvement. |

---

## 3. Target Users

| User Type | Profile | Core Need Solved by MVP |
| :--- | :--- | :--- |
| **Primary User (The Engineer)** | A full-stack AI engineer (analytical, design-focused) managing their own capital. | **Reliable Core Platform:** Provides a risk-guaranteed Python/FastAPI foundation for building advanced AI/ML features (e.g., LLM agent). |
| **Fund Manager** | Manager of a quantitative trading fund. | **Multi-Tenancy:** Manage multiple strategies and users within a fund structure. |
| **Trader** | Individual trader executing strategies. | **Execution & Monitoring:** Monitor signals and trade execution in real-time. |

---

## 4. In-Scope Functional Requirements (MVP)

The MVP is defined by the following core system behaviors, translated directly from the blueprint:

### 4.1. Core Signal Generation (SMC + MTF)

| Requirement | Description (Behavior) | Blueprint Reference |
| :--- | :--- | :--- |
| **F1.1** | The system must establish a Macro Bias (Long/Short) based on Price vs. EMA200 confluence on the 4H/D timeframes. | Macro bias (filter), Rule A |
| **F1.2** | The system must identify a Setup Zone (Confluence Zone) using 4H/1H Fibonacci (50%-61.8%) that overlaps with an SMC element (Order Block or FVG). | Setup zone, Rule B |
| **F1.3** | The system must wait for a 15m "Vector" candle confirmation where the `Body-to-Wick Ratio (Rv)` exceeds a set `threshold` (default 0.70) before entry. | Trigger, Rule C |
| **F1.4** | The system must reject trades if the confluence zone requirement (F1.2) is not met. | Setup zone, Rule B |

### 4.2. Absolute Risk & Position Sizing Engine

| Requirement | Description (Behavior) | Blueprint Reference |
| :--- | :--- | :--- |
| **F2.1** | The system must calculate Stop Loss (SL) distance based on a volatility-aware approach using `ATR(14, 15m) × M` (M=1.75 default). | Stop & Size, Rule D |
| **F2.2** | The system must strictly enforce an **Absolute Risk Cap of $10 per trade** (`Lot = $10 / SL_distance_in_USD`). | Hard cap, Rule D / Sec 4 |
| **F2.3** | The system must **reject a trade** if the calculated lot size is less than the minimum tradable lot (0.01). | Rejection Logic, Rule D / Sec 4 |
| **F2.4** | The system must **reject a trade** if the ATR-based Stop Loss distance exceeds 100 pips (Volatility Guardrail). | Volatility-aware stops, Sec 4 |

### 4.3. Backtesting & Reporting

| Requirement | Description (Behavior) | Blueprint Reference |
| :--- | :--- | :--- |
| **F3.1** | The system must enable vectorized backtesting (Vectorbt) with a parameter grid sweep for core parameters (EMA, ATR Mult, Rv Threshold). | Optimization Plan, Sec 5 |
| **F3.2** | The backtesting environment must ensure **no look-ahead bias** via deterministic MTF resampling and indicator alignment. | Look-ahead protection, Sec 5 |
| **F3.3** | The system must generate a basic Trade Log and Scorecard (MAE/MFE, WinRate, MDD, Sharpe) after each backtest run. | Monitoring & Scorekeeping, Sec 2 |

---

## 5. Phase 3: Advanced & Autonomous Capabilities

The following features are prioritized for the next major release (Phase 3), transforming the system into a professional, intelligent trading engine.

### 5.1. Advanced Backtesting
| Feature | Details |
| :--- | :--- |
| **Monte Carlo Simulation** | Stress-test strategies using randomized trade sequences and curve fitting analysis to ensure robustness. |
| **Automated Optimization** | "Grid Search" and genetic algorithms to automatically tune parameters (EMA, RSI, TP/SL) for maximum Sharpe/Return. |
| **Walk-Forward Analysis** | Verify strategy stability by simulating "out-of-sample" performance over rolling time windows. |

### 5.2. Realtime Autonomous Bot (24/7)
| Feature | Details |
| :--- | :--- |
| **Autonomous Supervisor** | A 24/7 background process (`LiveRunner`) that manages the Oanda connection, triggers strategy loops, and handles error recovery without human intervention. |
| **Order Execution Engine** | Low-latency order placement with precise slippage control and retry logic. |
| **State Persistence** | Robust recovery from crashes or restarts, ensuring no signal or trade state is lost. |

### 5.3. AI Integration (LLM & Algo)
| Feature | Details |
| :--- | :--- |
| **LangChain Agents** | Use LangChain to orchestrate complex reasoning loops (e.g., "Analyze News" -> "Check Trend" -> "Formulate Opinion"). |
| **Custom Models** | Integration of fine-tuned models or custom SLMs (Small Language Models) specifically trained on XAU/USD behavior. |
| **Narrative Trading** | Filter technical signals using AI-generated narrative bias (e.g., "Reject Longs if Fed is Hawkish"). |

---

## 6. User Stories (MVP)

As the **AI Engineer**, I want to...

| ID | User Story | Acceptance Criteria (Testable) |
| :--- | :--- | :--- |
| **US1** | ...define a wide range of strategy parameters, so I can efficiently sweep for the most robust settings using Vectorbt. | Parameter sweep runs successfully and produces a clean result table for [EMA, ATR, Rv] permutations. |
| **US2** | ...receive a signal only when 4H/1H Fibo zones align with a detected SMC block, so I can ensure high-confluence entries. | Backtest trade log shows entries only when Macro Bias, Setup Zone, and Trigger conditions were met simultaneously. |
| **US3** | ...input a risk check to the system, so that the $10 cap is never violated and my lot size is calculated correctly. | The `/risk/check` API endpoint returns `can_execute=false` for any trade proposal violating the $10 cap or the 0.01 min lot rule. |
| **US4** | ...ensure the backtest uses only historical data, so that the performance metrics are a true reflection of the strategy's edge. | All indicators are proven non-look-ahead via the deterministic MTF resampling check. |
| **US5** | ...see key metrics like Sharpe Ratio and Max Drawdown, so I can judge the viability of the optimized parameter sets. | Final backtest run successfully persists Sharpe, MDD, WinRate to the `StrategyRun` entity. |

---

## 7. Release Criteria (Go/No-Go)

The MVP is ready to proceed to the next development phase (Planning/Technical Design) when all of the following are met:

1.  **[SDD]** All core specification files (`01_architecture.md`, `03_data_model.yaml`, `04_api_spec.yaml`, `08_execution_rules.md`) are complete and validated by the primary stakeholders.
2.  **[Risk]** The core risk guardrail logic (F2.1 - F2.4) is coded, unit-tested, and verified to be non-violable in simulation.
3.  **[Backtest]** The Vectorbt backtesting harness is operational and can successfully run a parameter sweep without look-ahead bias.
4.  **[Metric]** Success Goal G2 (Sharpe > 0.8) has been achieved on at least one parameter set from the initial sweep.