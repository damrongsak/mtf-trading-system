# Benchmarking Strategy: Cross-Phase Accuracy Monitoring

To ensure the evolution of Olympus Predictor is data-driven, we implement a multi-stage benchmarking strategy.

## 1. Baseline Definitions

Each phase must be compared against the preceding version and a "Naive" baseline.

| Baseline | Strategy | Purpose |
| :--- | :--- | :--- |
| **Naive** | $P_{t+k} = P_t$ | Sanity check for drift. |
| **Classical** | Pure SARIMAX(1,1,1) | Measure linear dominance. |
| **Phase 0** | Absolute Price LSTM | Measure impact of Log-Return transform. |
| **Phase 1** | Hybrid + Gaussian Residual | Current Gold Standard. |

## 2. Key Performance Indicators (KPIs)

We track metrics in both **Return Space** and **Price Space**:

-   **RMSE / MAPE**: On absolute price (User-facing).
-   **Directional Accuracy (Hit Ratio)**: Ability to predict the correct candle sign.
-   **Expected Calibration Error (ECE)**: Measure how well the `sigma_lr` maps to actual volatility.
-   **Minimax Regret**: Evaluation of forecast error against the "Best Possible" execution.

## 3. Automated Comparison Pipeline

Triggered weekly or upon new model deployment:

1.  **Backtest Generation**: Run the last 30 days of H1/M15 data through $M_{v-1}$ and $M_{v}$.
2.  **Metric Aggregation**: 
    - Output average error per step ($t+1$ to $t+n$).
    - Plot Error Distribution (Heteroskedasticity check).
3.  **Governance**: 
    - If $M_{v}$ error > $M_{v-1}$ error + 15% margin, rollback is triggered or manual audit required.
    - If Bias > 0.5%, recalibrate Feature selection.

## 4. Phase-Specific Comparison Targets

| Comparison | Expected Improvement | Metric |
| :--- | :--- | :--- |
| Phase 1 vs Phase 0 | Stationarity | Normalized MSE |
| Phase 2 vs Phase 1 | Context Awareness | Attention Score Correlation |
| Phase 4 vs Phase 2 | Information Gain | Transfer Entropy |

---
*Created for Olympus Predictor Evolution Roadmap*
