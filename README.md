# MTF Olympus (v2.1)

**Status:** ✅ Alpha Ecosystem Live (Phase 2 Completed)  
**Next:** Phase 5 - Strategy Execution  
**License:** [Apache 2.0](LICENSE)

# Start with Why: The MTF Olympus Story

## The Why: Breaking the Cycle of Gambler's Ruin

Most retail traders fail not because they lack intelligence, but because they are fighting a war with broken tools. They buy "signals" from gurus—buying fish instead of learning how to fish. They use backtesting software that lies to them, showing beautiful equity curves that crumble the moment real money is on the line (curve fitting). And most fatally, they have no defense against their own psychology; when they tilt, they lose everything.

**MTF Olympus exists to democratize the institutional "Edge".**

We believe that wealth creation shouldn't be a gamble. It should be an engineering discipline. We believe that if you give a retail trader the same tools used by a quantitative hedge fund—Game Theoretic Risk Management, Walk-Forward Validation, and AI-Driven Psychological Coaching—they can stop gambling and start building a legacy.

**We don't build trading bots. We build Fund Managers.**

---

## The Vision: An Operating System for Wealth

MTF Olympus is not a tool; it is an **Operating System**. Just as Windows or macOS manages the complexity of hardware so you can run applications, Olympus manages the complexity of the Market so you can run **Strategies**.

### The 5 Pillars of the OS

1.  **The Foundry (Creation)**: Standardized "Lego Blocks" for strategy creation. No coding required, just logic.
2.  **The Alpha Engine (Research)**: **[NEW]** AST-based expression engine (`rank`, `ts_max`) for designing statistical factors.
3.  **The Proving Ground (Truth)**: Rigorous Walk-Forward Validation to prevent overfitting.
4.  **The Risk Citadel (Survival)**: Game Theoretic Risk Management engine using **Minimax Regret** & **Portfolio Risk Parity**.
5.  **The AI Coach (Discipline)**: Psychological intervention via **Mental Hand History** to detect "Tilt".

---

## 🏗️ System Architecture

The system is organized into a 5-layer stack:

| Layer | Name | Description | Service |
| :--- | :--- | :--- | :--- |
| **L1** | **Probability** | Statistical Analysis & Data Ingestion | Data Pipeline |
| **L2** | **Structure** | Strategy Logic definition & Standardized Blocks | Strategy Foundry |
| **L3** | **Context** | Validation, Walk-Forward Analysis, Market Regime | Proving Ground |
| **L4** | **Risk** | Game Theoretic Risk Management (Minimax) | Risk Citadel |
| **L5** | **Intelligence** | Psychological Coaching & Reasoning | AI Analyst |

### Microservices

| Service | Tech Stack | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Modern dashboard for Alpha Lab, Foundry, and AI Coach. |
| **API Gateway** | Python (FastAPI) | Central entry point, Auth (JWT), and request routing. |
| **Strategy Core** | Python (Vectorbt) | Implements Alpha Engine (Athena) and Foundry logic. |
| **Execution** | Python (FastAPI) | Implements Risk Citadel and Execution Edge. |
| **AI Analyst** | Python (LangGraph) | Implements AI Coach (gemini-2.5-flash) & Strategy Advisor. |
| **Data Pipeline** | Python (Redis) | L1 Probability Layer with Smart Latch (Atomic Consistency). |
| **Database** | PostgreSQL 15 | Relational data + `pgvector` for RAG. |

---

## 📂 Project Structure

```bash
mtf-trading-system/
├── services/               # Backend Microservices
│   ├── api-gateway/        # Auth & API Routing
│   ├── strategy-core/      # L2 Structure & L3 Context
│   ├── execution/          # L4 Risk & Execution Edge
│   ├── ai-analyst/         # L5 Intelligence
│   └── data-pipeline/      # L1 Probability
├── frontend/               # Next.js Web App
├── infra/                  # Nginx, Docker configs
├── specs/                  # SDD Specifications (Source of Truth)
└── docker-compose.yml      # Local Orchestration
```

---

*   `services/`: Backend microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `data-pipeline`).
*   `frontend/`: Next.js web application.
*   `specs/`: SDD source of truth.

## 📡 Real-Time Data Streaming

The system includes a high-performance **Tick Streamer** built on the OANDA v20 SDK and Redis Pub/Sub.

- **Service**: `tick-streamer` (Dockerized)
- **Mechanism**: Dedicated background worker fetching ticks from OANDA.
- **Data Distribution**: Publishes to Redis channels `market_data:tick:{SYMBOL}`.
- **Dynamic Configuration**: Automatically loads active symbols from the `market_symbols` database table.

### Monitoring Ticks
To verify real-time data flow, use the Redis CLI:
```bash
docker compose exec redis redis-cli PSUBSCRIBE "market_data:tick:*"
```

## 🛠️ Development Workflow

### Prerequisites
-   Docker & Docker Compose
-   Node.js v22+
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
    Register via the frontend or use the API.

---

## 🧩 Spec-Driven Development (SDD)

This project strictly follows SDD. **Do not write code without updating specs first.**

-   `specs/00_product_requirements.md`: The WHAT and WHY.
-   `specs/01_architecture.md`: The High-Level Design.
-   `specs/03_data_model.yaml`: Database Schema definitions.
-   `specs/04_api_spec.yaml`: API Contracts (OpenAPI).
-   `specs/10_implementation_status.md`: Progress Tracker.

---

## ⚠️ Disclaimer

**USE AT YOUR OWN RISK.** This software is for educational purposes only. Automated trading carries significant financial risk. The authors assume no responsibility for trading losses.