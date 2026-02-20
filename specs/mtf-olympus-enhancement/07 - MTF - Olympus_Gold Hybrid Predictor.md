# Spec-Driven Development: Project Olympus (Gold Hybrid Predictor)

**Project Mission:** To engineer a high-fidelity financial forecasting system for Gold (GC=F) that out-competes traditional econometrics by isolating linear trends via SARIMAX and capturing non-linear "Black Swan" residuals via a Deep Learning Residual Learner.

---

## 1. Specification (The Source of Truth)

### Product Mission
To provide institutional-grade gold price forecasting by synthesizing macroeconomic indicators (Oil, EUR/USD, TIPS) with historical price memory to assist in risk management and entry-point optimization.

### Core Principles (SDD)
- **Spec as Code:** This document is the absolute source of truth for the implementation.
- **Traceability:** Every feature in the code must map to a Requirement ID (REQ).
- **Human-in-the-loop:** AI agents perform the heavy lifting of training; human engineers validate the "Regime Shift" logic.

### Functional Requirements (EARS Syntax)
| ID | Trigger | Requirement |
|:---|:---|:---|
| **REQ-01** | When a prediction request is received | The system shall compute a 5-day horizon forecast combining SARIMAX + LSTM-Residuals. |
| **REQ-02** | While the markets are open (UTC) | The system shall ingest live data every 1 hour via the Data Ingestion service. |
| **REQ-03** | Where market volatility exceeds 2.5% | The system shall flag the forecast as "High Uncertainty" and trigger a sentiment analysis override. |
| **REQ-04** | Every Sunday 23:00 UTC | The system shall retrain the Boruta-SHAP feature selector to adapt to the new market regime. |

---

## 2. Technical Implementation Plan: "Olympus" Architecture

| Component | Technology | Description |
|:---|:---|:---|
| **Data Orchestrator** | `yfinance` + `Pandas` | Fetches Gold, WTI Oil, EUR/USD, and 10Y TIPS (Real Yields). |
| **Linear Base** | `SARIMAX` | Captures seasonality (S) and linear autocorrelation. |
| **Feature Selection** | `Boruta-SHAP` | Replaces Stepwise Regression to detect non-linear dependencies. |
| **Residual Learner** | `Stacked LSTM` | Learns the delta between SARIMAX predictions and actual spot prices. |
| **Inference Wrapper** | `FastAPI` | Asynchronous serving of predictions. |
| **Operations** | `Docker Compose` | Isolated environments for `Olympus-API` and `Olympus-Trainer`. |

---

## 3. Granular Task List

- [ ] **Data Layer (Task-D1):** Implement asynchronous fetching for multi-ticker data (GC=F, CL=F, EURUSD=X, ^TNX).
- [ ] **Feature Engine (Task-F1):** Calculate advanced indicators: Bollinger Bands, RSI, and **VIX Correlation**.
- [ ] **Linear Training (Task-L1):** Optimize SARIMAX (p,d,q)(P,D,Q)s hyperparameters via GridSearch.
- [ ] **Residual Training (Task-R1):**
    - [ ] Calculate `Actual_Price - SARIMAX_Forecast` as target.
    - [ ] Train Stacked LSTM on scaled residuals using a 20-day lookback.
- [ ] **Go-Live API (Task-A1):**
    - [ ] Build `/predict` endpoint.
    - [ ] Build `/metrics` endpoint to track MAE (Mean Absolute Error) over time.
- [ ] **Orchestration (Task-O1):** Define Docker volumes for atomic model swaps (zero-downtime retraining).

---

## 4. Implementation Guidelines (The "Best Idea" Redesign)

### The "Olympus" Residual Strategy
Standard models try to predict the price directly. **Olympus** assumes the market is efficient for 90% of the time (SARIMAX handles this). We only use the LSTM to predict the **Inefficiency** (the Residual).
- **Constraint:** The LSTM *must* have a Dropout rate of at least 0.3 to prevent overfitting on market noise.
- **Constraint:** Scalers must be persisted as separate artifacts to prevent feature leakage during retraining.

---

## 5. Review & Validation

### Automated Validation (SDD-V)
1. **Backtest Check:** The system must demonstrate an RMSE improvement of at least 15% over a naive ARIMA baseline on 2024-2025 data.
2. **Docker Check:** `docker-compose up` must initiate a successful model load in under 30 seconds.
3. **API Check:** Endpoint `/predict` must respond within <200ms under load.

### Project - Olympus Metadata
| Metadata | Value |
|:---|:---|
| **Version** | 1.2.0-Alpha |
| **Lead Engineer** | Gemini (Full-Stack AI) |
| **Methodology** | Spec-Driven Development (SDD) |
| **Status** | Implementation-Ready |