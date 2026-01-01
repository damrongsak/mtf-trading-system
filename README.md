# MTF Olympus (v2.0)

**Status:** In Development (Phase 6 - Portfolio Management & Transaction Tracking)  
**License:** [Apache 2.0](LICENSE)

**MTF Olympus** is an **Operating System (OS)** for wealth creation. It democratizes the sophisticated tools used by institutional hedge funds—**Game Theoretic Risk Management**, **Walk-Forward Validation**, and **AI-Driven Psychology Coaching**—allowing individuals to act as their own Quant Fund Managers.

It evolves the previous "Phoenix Alpha Engine" into a distributed platform that separates Logic (Foundry), Validation (Proving Ground), Risk (Citadel), Execution (Edge), and Psychology (Coach).

---

## 🏛️ The 5 Pillars of Olympus

The platform is built on five functional pillars:

1.  **The Strategy Foundry**: Standardized "Lego Blocks" for creating strategies (no ad-hoc code).
2.  **The Proving Ground**: Rigorous Walk-Forward Validation to prevent overfitting (Strategies must achieve a Robustness Score > 80).
3.  **The Risk Citadel**: Game Theoretic Risk Management engine using **Minimax Regret** & **Portfolio Risk Parity**.
4.  **The Execution Edge**: Smart Order Routing and Liquidity analysis.
5.  **The AI Coach**: Psychological intervention via **Mental Hand History** to detect "Tilt" and guide the user back to "A-Game".

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
| **Frontend** | Next.js 16 (React 19) | Modern dashboard for Foundry, Citadel, and AI Coach. |
| **API Gateway** | Python (FastAPI) | Central entry point, Auth (JWT), and request routing. |
| **Strategy Core** | Python (Vectorbt) | Implements Foundry and Proving Ground logic. |
| **Execution** | Python (FastAPI) | Implements Risk Citadel and Execution Edge. |
| **AI Analyst** | Python (LangGraph) | Implements AI Coach (Gemini 1.5 Pro). |
| **Data Pipeline** | Python (Redis) | L1 Probability Layer (Real-time & Historical Data). |
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

## 🛠️ Getting Started

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