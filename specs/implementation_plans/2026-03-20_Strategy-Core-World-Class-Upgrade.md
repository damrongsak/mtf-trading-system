# Implementation Plan: Strategy Core World-Class Upgrade (v2.8)

## 1. Overview
This plan outlines the enhancements to the `strategy-core` service to transition it from a microservice into an institutional-grade "Strategy Operating System". The upgrade focuses on advanced quantitative integration (Kelly, PyPortfolioOpt, Monte Carlo) and a robust strategy lifecycle (Foundry -> Proving Ground -> Shadow -> Live).

## 2. Objectives
- **Advanced Quant Integration**: Seamlessly incorporate Kelly Criterion, Monte Carlo, and PyPortfolioOpt into the strategy lifecycle.
- **Robustness Engineering**: Implement automated Walk-Forward Analysis (WFA) and "Minimax Regret" risk filtering.
- **Workflow Efficiency**: Standardize the "Logic Test" (Backtest) and "Flow Test" (Internal Signal) APIs.
- **Multi-Asset Intelligence**: Enable portfolio-level optimization for multiple active strategies.

## 3. Spec Changes
- **04_api_spec.yaml**:
    - Add `/backtest/wfa` for Walk-Forward Analysis.
    - Add `/backtest/optimize/portfolio` for PyPortfolioOpt weighting.
    - Add `/backtest/monte-carlo/bootstrap` for enhanced simulation.
- **08_execution_rules.md**:
    - Define "Minimax Regret" threshold rules.
    - Standardize Kelly Fraction (Half-Kelly) as a system-wide default.

## 4. Implementation Steps

### Phase 1: Institutional Quant Layer (Citadel & Proving Ground)
1.  **Enhance Monte Carlo (`app/analysis/monte_carlo.py`)**:
    - Add Bootstrap resampling (resampling with replacement).
    - Add Regime-specific resampling (Trending vs Ranging).
    - Implement Equity Curve Envelopes (Confidence Bands).
2.  **Portfolio Optimization (`app/analysis/optimizer.py`)**:
    - Extend `PortfolioOptimizer` to handle multiple strategy equity curves.
    - Integrate `PyPortfolioOpt`'s Black-Litterman model if possible (Future).
3.  **WFA Hardening (`app/proving_ground/validator.py`)**:
    - Finalize `WalkForwardValidator` with automated reporting of "Robustness Scores".

### Phase 2: Strategy Foundry & Alpha Engine
1.  **Vectorized Base Class**:
    - Create `app/foundry/vector_base.py` to allow strategies to run in O(1) time across entire history using `vectorbt`.
2.  **Minimax Risk Filter**:
    - Implement `app/quant/minimax.py` to calculate "Worst-case Regret" for signals.
    - Integrate this into `FleetManager` signal dispatching.

### Phase 3: API & Workflow Standardization
1.  **Logic Test (Backtest API)**:
    - Standardize `POST /api/v1/backtest/run` to return unified JSON metrics compatible with the Frontend Radar charts.
2.  **Flow Test (Internal Signals API)**:
    - Formalize `POST /api/v1/internal/signals` for E2E pipeline verification (Strategy -> Gateway -> Execution -> DB).

## 5. Verification Plan
1.  **Unit Tests**:
    - `pytest tests/test_monte_carlo.py`
    - `pytest tests/test_portfolio_optimizer.py`
2.  **Contract Tests**:
    - Verify `/backtest/run` against `04_api_spec.yaml`.
3.  **E2E Flow Test**:
    - Run the `curl` commands provided in the user prompt to verify both Logic and Flow paths.

## 6. Documentation
- Update `docs/STRATEGY_DEV_GUIDE.md` with Kelly and Monte Carlo usage instructions.
- Add a new `docs/PORTFOLIO_OPTIMIZATION_GUIDE.md`.
