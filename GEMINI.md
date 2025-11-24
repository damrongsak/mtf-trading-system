# GEMINI.md

## 🚀 Project Overview
**MTF Trading System** is a sophisticated algorithmic trading platform designed for XAU/USD (Gold) trading. It utilizes a **Multi-Timeframe (MTF)** analysis approach combined with **Smart Money Concepts (SMC)**.

The project distinguishes itself through:
1.  **Spec-Driven Development (SDD):** Architecture and data contracts are defined in YAML/Markdown specs *before* implementation.
2.  **AI-First Design:** Integrates Google Gemini (via Vertex AI) for semantic market analysis and reasoning.
3.  **Microservices Architecture:** Modular Python services for strategy, execution, and AI analysis, fronted by a Next.js dashboard.

## 🏗️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Dashboard for signals, trade logs, and backtest visualization. |
| **API Gateway** | Python (FastAPI) | Entry point for all backend operations; routes to internal logic. |
| **Strategy Core** | Python (Vectorbt, Pandas) | Implements MTF/SMC logic, signal generation, and backtesting. |
| **AI Analyst** | Python (Gemini Pro) | Analyzes market context and news for narrative-based insights. |
| **Database** | PostgreSQL 15 + pgvector | Stores relational trade data and vector embeddings. |
| **Vector Store** | Qdrant | Handles similarity search for pattern recognition and RAG. |
| **Infrastructure** | Docker Compose, Nginx | Container orchestration and reverse proxying. |
| **Cloud Target** | GCP (Cloud Run, SQL) | Production environment (Project: `line-bot-2b383`). |

### 📂 Directory Structure
*   `specs/`: **Source of Truth**. Contains Architecture (`00`), Data Models (`01`), API Contracts (`02`), and Logic Rules (`04`).
*   `services/`: Backend microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `execution`).
*   `frontend/`: Next.js web application.
*   `infra/`: Infrastructure configurations (Nginx, etc.).
*   `docker-compose.yml`: Orchestration for local development.

## 🛠️ Development Workflow

### 1. The SDD Process (Crucial)
**Do not write code without checking specs first.**
1.  **Read Specs:** Check `specs/` for defining behavior.
2.  **Update Specs:** If a new feature is needed, modify `01_data_model.yaml` or `02_api_spec.yaml` first.
3.  **Implement:** Scaffold code based on the updated specs.

### 2. Running the System
**Prerequisites:** Docker & Docker Compose, Node.js (pnpm).

*   **Full Stack (Recommended):**
    ```bash
    docker compose up --build
    ```
    *   Frontend: `http://localhost:3000`
    *   API Docs: `http://localhost:8000/docs`
    *   Qdrant Dashboard: `http://localhost:6333/dashboard`

*   **Frontend Only:**
    ```bash
    nvm use 22
    pnpm install
    pnpm --filter frontend dev
    # Or: pnpm --filter frontend build / test
    ```

*   **Backend Service (Standalone):**
    ```bash
    cd services/api-gateway
    # Create venv and install requirements first
    uvicorn app.main:app --reload
    ```

### 3. Testing
*   **Backend:** `pytest` (Contract tests derived from specs).
*   **Backtesting:** `vectorbt` based simulations.

### 4. Database Migration (Alembic)
To apply schema changes to the database:

1.  **Connect to the API Gateway service:**
    ```bash
    cd services/api-gateway
    ```

2.  **Set the Database URL (if running locally against Docker DB):**
    ```bash
    export DATABASE_URL=postgresql://trader:trader@localhost:5432/mtf_db
    ```

3.  **Create a new migration (after modifying models):**
    ```bash
    ./venv/bin/alembic revision --autogenerate -m "Description of changes"
    ```

4.  **Apply migrations:**
    ```bash
    ./venv/bin/alembic upgrade head
    ```

## 🔑 Key Logic & Constraints (from PRD)
*   **Risk Management:** Strict **$10 max risk per trade**. Minimum lot **0.01**.
*   **Strategy:**
    *   **Macro Bias:** 4H/Daily Price vs EMA200.
    *   **Setup:** 4H/1H Fibo (50-61.8%) + SMC Order Block.
    *   **Trigger:** 15m Candle with high Body-to-Wick ratio.
*   **Status:** The project is evolving. While the PRD defines a strict MVP, the codebase includes "Future" features like the AI Analyst and Frontend, indicating active expansion.

## � Inspiration & Examples
*   **Gridbot AI Volatility Harvester:** Check `example/gridbot-ai-volatility-harvester` for frontend UI/UX inspiration (Vite + React).

## �📝 Common Commands
| Action | Command |
| :--- | :--- |
| **Start Full Stack** | `docker compose up --build` |
| **Start Backend Only** | `docker compose up api execution` |
| **Start Frontend Only** | `docker compose up frontend` |
| **Rebuild Specific** | `docker compose up --build <service_name>` |
| **Stop All** | `docker compose down` |
| **Deploy** | `./deploy.sh` |
| **Connect to DB** | `docker exec -it pgvector psql -U trader -d mtf_db` |
