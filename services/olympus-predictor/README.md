# Olympus Predictor: Hybrid Multi-Timeframe Gold Forecasting

[![Status](https://img.shields.io/badge/Status-v2.1.0--alpha-brightgreen)](https://github.com/damrongsak/mtf-trading-system)
[![Architecture](https://img.shields.io/badge/Architecture-Hybrid_Attention_Regime-blue)](docs/architecture.md)
[![Target](https://img.shields.io/badge/Target-Log--Returns-orange)](docs/theory.md)

**Olympus Predictor** is a high-fidelity quantitative forecasting engine for XAU/USD (Gold). It utilizes a decoupled **Hybrid-Linear-Nonlinear Pipeline** designed to bridge the gap between classical econometrics and deep learning residuals, optimized for institutional risk management.

---

## 🔬 Core Architecture (v2.1.0)

The system operates on an "Ensemble-Residual" paradigm:

1.  **Linear Base (SARIMAX)**: Captures auto-regressive properties and exogenous seasonal trends.
2.  **Market Regime Detector (HMM)**: Classifies market states (Trend/Range/Volatile) using GARCH(1,1) volatility.
3.  **Dynamic Macro Forecaster (VAR)**: Projects exogenous macro inputs (Oil, EURUSD, Bond Yields) for multi-step coherence.
4.  **Non-linear Correction (Self-Attention LSTM)**: A distributional LSTM that models heteroskedastic residuals, enhanced with **Self-Attention** and **Sentiment Analysis** scores.
5.  **Risk-Adjusted Loss**: Optimized using a custom objective function that penalizes "Directional Regret" to maximize Sharpe Ratio.

### Mathematical Foundation
$$ \ln\left(\frac{P_t}{P_{t-1}}\right) = \text{SARIMAX}(\text{Base}) + \text{Attn-LSTM}(\epsilon_{t} | \text{Macro}, \text{Regime}, \text{Sentiment}) $$
$$ \text{Signal}_{\text{conf}} = \frac{\mathbb{E}[\text{Return}]}{\sqrt{\text{Var}[\text{Return}]}} $$

---

## 🏗️ AI-Ops & Infrastructure

-   **Asynchronous Training**: Decoupled from API via **Redis Task Queue**.RETRAIN doesn't block inference.
-   **Centralized Feature Store**: Multi-tier Redis caching for technical indicators and sentiment aggregates.
-   **Model Versioning**: Automated snapshotting of models (`versions/v_timestamp`) with metadata and metrics.
-   **Institutional Traceability**: Audit logging of every signal generation event with high-fidelity context.

---

## 🛠 Tech Stack

-   **Logic**: Python 3.12+ (Typed)
-   **Forecasting**: `statsmodels`, `arch` (GARCH), `hmmlearn` (HMM)
-   **Deep Learning**: `PyTorch` (Self-Attention LSTM)
-   **Messaging**: `Redis` (Queue + Feature Store)
-   **Database**: `PostgreSQL` (Audit Logs + Sentiment)

---

## 📊 API Documentation

### `POST /predict`
Multi-step price and volatility forecast.
- **Response**: `prices`, `sigma_lr`, `sentiment`, `model_version`.

### `POST /signal` (Phase 4)
Institutional signal generation.
- **Response**: `direction` (BUY/SELL), `target`, `stop_loss`, `confidence` (0-1).

### `POST /train`
Queues an async training job. Returns `job_id`.

### `GET /train/status/{job_id}`
Monitor training progress and result metrics.

---

## 🚀 Installation
```bash
# Run the predictor and worker via Docker
docker compose up -d --build olympus-predictor predictor-worker
```

---

## 📜 Research & References
- Phase 1-4 Walkthroughs: [brain artifacts](../../.gemini/antigravity/brain/27717bee-9273-4c84-bcc4-0688072b0f8c/)
- Full Evolution Roadmap: [docs/roadmap.md](../../specs/mtf-olympus-enhancement/07.01%20Olympus%20Predictor_%20Evolution%20Roadmap.md)

---
**Maintained by Quant Team @ MTF Olympus**
