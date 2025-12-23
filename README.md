# MTF Trading System (Phoenix Alpha Engine)

**Status:** Phase 2 Complete (Ready for Live Testing)
**License:** [Apache 2.0](LICENSE)

The **MTF Trading System** is a sophisticated algorithmic trading platform designed for XAU/USD (Gold). It utilizes a **Multi-Timeframe (MTF)** analysis approach combined with **Smart Money Concepts (SMC)**, enforced by a strict risk management engine.

Built for the **AI Era**, it bridges the gap between discretionary trading and automated execution, featuring a "Psychological MRI" journal, an AI Market Analyst agent (Gemini Pro), and a robust microservices architecture.

## 🚀 Key Features

### 🛡️ Risk & Execution
-   **Strict Risk Management:** Pre-trade validation ensuring no trade exceeds the defined risk limit.
-   **Configurable Risk Profiles:** User-defined max risk per trade (e.g., $10, 0.5%) and Max Drawdown limits per strategy.
-   **Volatility Guards:** Dynamic Stop Loss based on ATR; trades rejected if volatility is too high (>100 pips).
-   **Multi-Broker Support:** Securely manage multiple OANDA/Binance accounts with AES-256 credential encryption.

### 🧠 Intelligence & Analysis
-   **AI Analyst:** "Market Observer" agent (Gemini 1.5 Pro) that provides narrative analysis of chart patterns and news.
-   **SMC Engine:** Automated detection of Order Blocks, Fair Value Gaps (FVG), and Liquidity Sweeps across M15, H1, H4 timeframes.
-   **Trading Journal:** Structured "Mental Hand History" wizard to track psychological state (Tilt, Fear, Greed) alongside technical performance.

### ⚡ Architecture & Performance
-   **Multi-Tenancy:** Support for multiple users and funds with Role-Based Access Control (RBAC).
-   **Strategy Registry:** JSON-configurable strategy templates (e.g., SMC_Basic, MACD_Cross) allowing multiple concurrent instances.
-   **Real-time Dashboard:** Live equity curves, P&L stats, and signal monitoring pushed via WebSockets (Redis Pub/Sub).
-   **Event-Driven Data Pipeline:** Centralized ingestion of market data (OANDA v20) distributed to all services.

## 🏗️ System Architecture

| Service | Tech Stack | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Modern, responsive dashboard for signals, charts, and configuration. |
| **API Gateway** | Python (FastAPI) | Central entry point, Auth (JWT), and request routing. |
| **Strategy Core** | Python (Pandas/Vectorbt) | Signal generation, Backtesting engine, and Indicator calculation. |
| **Execution** | Python (FastAPI) | Order routing, Risk constraints, and Broker connectivity. |
| **Data Pipeline** | Python (Redis/Celery) | Real-time market data streaming and historical candle storage. |
| **AI Analyst** | Python (LangGraph) | LLM-based market reasoning and RAG (Qdrant). |
| **Database** | PostgreSQL 15 | Relational data (Users, Trades, Journals) + `pgvector` for RAG. |

## 📂 Project Structure

```bash
mtf-trading-system/
├── services/               # Backend Microservices
│   ├── api-gateway/        # Auth & API Routing
│   ├── strategy-core/      # Algo Logic & Backtesting
│   ├── execution/          # Broker Adapters & Risk Engine
│   ├── data-pipeline/      # Market Data Ingestion
│   └── ai-analyst/         # LLM Agent
├── frontend/               # Next.js Web App
├── infra/                  # Nginx, Docker configs
├── specs/                  # SDD Specifications (Source of Truth)
└── docker-compose.yml      # Local Orchestration
```

## 🛠️ Getting Started

### Prerequisites
-   Docker & Docker Compose
-   Node.js v22+ (for local frontend dev)
-   `uv` (Python package manager)

### Quick Start (Full Stack)
1.  **Clone the repo:**
    ```bash
    git clone https://github.com/your-org/mtf-trading-system.git
    cd mtf-trading-system
    ```

2.  **Environment Setup:**
    Duplicate `.env.example` to `.env` and fill in your keys (Gemini API, OANDA Token, Postgres Config).

3.  **Run with Docker Compose:**
    ```bash
    docker compose up --build
    ```
    -   Frontend: `http://localhost:3000`
    -   API Docs: `http://localhost:8000/docs`

4.  **Create Admin User:**
    Use the `/api/v1/auth/register` endpoint or the frontend Register page to create your first user.

5.  **Configure Strategy:**
    -   Go to **Settings -> Broker Accounts** to add OANDA credentials.
    -   Go to **Strategies -> New Strategy** to configure and launch an SMC instance.

## 🧩 Spec-Driven Development (SDD)

This project strictly follows SDD. **Do not write code without updating specs first.**

-   `specs/00_product_requirements.md`: The WHAT and WHY.
-   `specs/01_architecture.md`: The High-Level Design.
-   `specs/03_data_model.yaml`: Database Schema definitions.
-   `specs/04_api_spec.yaml`: API Contracts (OpenAPI).
-   `specs/10_implementation_status.md`: Progress Tracker.

## 🤝 Contribution

1.  Pick a task from `specs/10_implementation_status.md` (or create a new RFC).
2.  Update the relevant Spec file in a PR.
3.  Once the Spec is approved, implement the code.
4.  Submit PR with tests.

## ⚠️ Disclaimer

**USE AT YOUR OWN RISK.** This software is for educational purposes only. Automated trading carries significant financial risk. The authors assume no responsibility for trading losses.