# Olympus Predictor: Hybrid Multi-Timeframe Gold Forecasting

[![Status](https://img.shields.io/badge/Status-Phase1_Complete-brightgreen)](https://github.com/damrongsak/mtf-trading-system)
[![Architecture](https://img.shields.io/badge/Architecture-Hybrid_Linear_LSTM-blue)](docs/architecture.md)
[![Target](https://img.shields.io/badge/Target-Log--Returns-orange)](docs/theory.md)

**Olympus Predictor** is a high-fidelity quantitative forecasting engine for XAU/USD (Gold). It utilizes a decoupled **Hybrid-Linear-Nonlinear Pipeline** designed to bridge the gap between classical econometrics and deep learning residuals.

---

## 🔬 Core Architecture (v2.1)

The system operates on a "Residual Correction" paradigm:

1.  **Linear Base (SARIMAX)**: Captures the auto-regressive properties and exogenous seasonal trends of Log-Returns.
2.  **Non-linear Residual Correction (Gaussian LSTM)**: A distributional LSTM that models the heteroskedastic residuals left by the SARIMAX model.
3.  **Uncertainty Quantification**: Instead of point-estimates, the engine outputs a $(\mu, \sigma)$ pair, allowing for **Risk-Adjusted Execution** and confidence-based position sizing.

### Mathematical Foundation
$$ \ln\left(\frac{P_t}{P_{t-1}}\right) = \text{SARIMAX}(p,d,q, \text{Exog}) + \epsilon_{t} $$
$$ \epsilon_{t} \approx \text{LSTM}(\mu_{\epsilon}, \sigma_{\epsilon}) $$

---

## 🛠 Tech Stack for Quantitative Engineers

-   **Domain Logic**: Python 3.12+ (Typed)
-   **Linear Modeling**: `statsmodels` (State-Space SARIMAX)
-   **Deep Learning**: `PyTorch` (Distributional LSTM with NLL Loss)
-   **Feature Selection**: `Boruta` (SHAP-based shadow feature validation)
-   **Data Eng**: `asyncpg` (Direct Postgres Access), `Redis` (Caching Layer)
-   **Optimization**: `yfinance` for macro alignment, `vectorbt` (planned for backtesting)

---

## 📂 Project Structure

```bash
services/olympus-predictor/
├── src/app/
│   ├── api/             # FastAPI Routers & Pydantic Schemas
│   ├── core/            # Config (Settings), Logging, Global Context
│   ├── domain/          # THE BRAIN: Models, Features, Transformers
│   │   ├── models.py    # HybridPredictor & ResidualLSTM
│   │   ├── features.py  # Technical Indicators & Boruta Selection
│   │   └── transformers.py # Log-Return & Scale management
│   └── infrastructure/  # Data Loaders (DB/API/Redis)
├── models/              # Serialized artifacts (pth, pkl)
├── tests/               # Unit & Integration Suite
└── pyproject.toml       # UV Managed Dependencies
```

---

## 🚀 Getting Started (AI/Dev Engineers)

### Prerequisites
- Docker & Docker Compose
- `uv` (Fast Python package manager)

### Local Development
```bash
# Enter service directory
cd services/olympus-predictor

# Setup environment
uv sync

# Run standalone training (Development context)
uv run python -m src.app.main --train

# Run with Docker
docker compose up -d --build olympus-predictor
```

---

## 📊 API Documentation

### `POST /predict`
Returns a multi-step forecast with breakdown.
- **Request**: `{"symbol": "XAUUSD", "steps": 5}`
- **Response**:
    - `predictions`: Absolute price forecast.
    - `sigma_lr`: Log-Return volatility (Uncertainty).
    - `used_features`: Features selected via Boruta.

### `POST /train`
Trigger retraining on latest Gold and Macro data (CL=F, EURUSD=X, ^TNX).

---

## 📈 Benchmarking & Accuracy
| Metric | SARIMAX (Baseline) | Hybrid (Phase 1) | Target (Phase 2+) |
| :--- | :--- | :--- | :--- |
| **MAPE** | 2.1% | 1.4% | < 1.0% |
| **Directional Acc** | 52% | 58% | > 65% |
| **Calibration** | N/A | High (Gaussian NLL) | Multi-modal |

---

## 📜 Research & References
- Phase 1 White Paper: [Methodology of Hybrid Log-Returns](paper/Phase1_Hybrid_LogReturn.md)
- Institutional Enhancement Roadmap: [docs/roadmap.md](../../specs/mtf-olympus-enhancement/07.01%20Olympus%20Predictor_%20Evolution%20Roadmap.md)

---
**Maintained by Quant Team @ MTF Olympus**
