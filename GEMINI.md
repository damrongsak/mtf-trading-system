# GEMINI.md

## 🚀 Project Overview
**MTF Olympus (v2.0)** is a distributed quantitative trading platform designed for XAU/USD (Gold). It evolves the concept of a "Trading Bot" into a comprehensive **Wealth Operating System**, combining **Multi-Timeframe (MTF)** analysis with **Smart Money Concepts (SMC)** and **Game Theoretic Risk Management**.

The project distinguishes itself through:
1.  **Spec-Driven Development (SDD):** Architecture and data contracts are defined in YAML/Markdown specs *before* implementation.
2.  **AI-First Design:** Integrates **Google Gemini 2.5** (via Vertex AI) for semantic market analysis and psychological coaching.
3.  **Institutional Risk Engine:** Uses **Minimax Regret** and **Portfolio Risk Parity** (PyPortfolioOpt) instead of static lot sizes.
4.  **Microservices Architecture:** Modular Python services (FastAPI) for strategy, execution, and AI analysis, fronted by a Next.js 16 dashboard.

## 🏗️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Modern dashboard for Signals, Journal, and Backtesting. |
| **API Gateway** | Python (FastAPI) | Entry point for all backend operations; Auth (JWT) and routing. |
| **Strategy Core** | Python (Vectorbt, Pandas) | Implements SMC Logic, Market Structure, and Backtesting Engine. |
| **Execution Service** | Python (FastAPI, PyPortfolioOpt) | Handles trade execution and Smart Dynamic Risk sizing. |
| **AI Analyst** | Python (LangGraph, Gemini 2.5) | "Market Observer" Agent and RAG-based Journal analysis. |
| **Data Pipeline** | Python (Redis, Oanda v20) | Real-time StreamManager and OpenInterest ingestion. |
| **Database** | PostgreSQL 15 | Stores relational trade data and vector embeddings. |
| **Vector Store** | Qdrant | Handles similarity search for pattern recognition and RAG. |
| **Infrastructure** | Docker Compose, Nginx | Container orchestration and reverse proxying. |
| **Cloud Target** | GCP (Cloud Run, SQL) | Production environment. |

### 📂 Directory Structure
*   `specs/`: **Source of Truth**. Contains Architecture (`01`), Data Models (`03`), API Contracts (`04`), and Logic Rules (`08`).
*   `services/`: Backend microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `execution`, `data-pipeline`).
*   `frontend/`: Next.js web application.
*   `infra/`: Infrastructure configurations (Nginx, etc.).
*   `docker-compose.yml`: Orchestration for local development.

## 🛠️ Development Workflow

### 1. The SDD Process (Crucial)
**Do not write code without checking specs first.**
1.  **Read Specs:** Check `specs/` for defining behavior.
2.  **Update Specs:** If a new feature is needed, modify `03_data_model.yaml` or `04_api_spec.yaml` first.
3.  **Generate Code:**
    *   **Backend Models:** `services/api-gateway/scripts/gen_backend.sh`
    *   **Frontend Client:** `cd frontend && pnpm run gen:api`
4.  **Implement:** Scaffold code based on the updated specs and generated types.

### 2. Running the System
**Prerequisites:** Docker & Docker Compose, Node.js (pnpm), `uv` (for backend development).

*   **Install uv (first time only):**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

*   **Environment Setup Notes (WSL/Local):**
    *   **uv:** If `uv` is not in PATH, add `export PATH="$HOME/.local/bin:$PATH"` or run via `~/.local/bin/uv`.
    *   **Node/pnpm:** Managed via `nvm`. If commands are missing, run: `source ~/.nvm/nvm.sh`.

*   **Full Stack (Recommended):**
    ```bash
    docker compose up --build
    ```
    *   Frontend: `http://localhost:3000`
    *   API Docs: `http://localhost:8000/docs`
    *   Qdrant Dashboard: `http://localhost:6333/dashboard`

    > **Note:** If you encounter `npm` or `node` command errors locally, ensure NVM is loaded:
    > ```bash
    > export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    > ```

*   **Command Execution Strategy (Important):**
    *   **Backend Services (MANDATORY):** All backend commands MUST be run inside their respective Docker containers.
        *   **Syntax:** `docker compose exec <service_name> <command>`
        *   **Example (Test):** `docker compose exec strategy-core uv run pytest`
    *   **Frontend:** Can be run locally using `nvm` (Node v22) or via Docker.

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
    # Install dependencies (first time or when dependencies change)
    uv sync
    # Run the server
    uv run uvicorn app.main:app --reload
    ```

### 3. Testing
*   **Backend:** `uv run pytest` (Contract tests derived from specs).
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

### 5. Git Flow & Version Control
**Strictly follow this workflow for all changes:**
1.  **Checkout `dev` branch:** `git checkout dev`
2.  **Pull latest changes:** `git pull origin dev`
3.  **Create a feature branch:** `git checkout -b feature/your-feature-name`
4.  **Implement changes:** Follow SDD and Clean Code principles.
5.  **Commit changes:** Use descriptive commit messages (e.g., `feat: add user auth`, `fix: resolve db connection`).
6.  **Merge to `dev`:**
    ```bash
    git checkout dev
    git merge feature/your-feature-name
    git push origin dev
    ```

## 🔑 Key Logic & Constraints (Phases 1-28)
*   **Risk Management:** 
    *   **Smart Dynamic Risk:** 1% of NAV per trade, capped by Fund Limit.
    *   **Guardrails:** Risk-Reward Ratio (RRR) must be >= 1.5.
*   **Strategy (SMC):**
    *   **Macro Bias:** 4H/Daily Price vs EMA200.
    *   **Structure:** Liquidity Sweeps, Fair Value Gaps (FVG), and Order Blocks (OB).
    *   **Trigger:** 15m Candle confirmation inside an H1 POI.
*   **Monitoring:**
    *   **System Drift:** Monitors Rejection Rate (Skipped / Total Signals). Alert if > 80%.
    *   **AI Analyst:** Daily "Market Observer" briefings and drift analysis.

## ✨ Completed Features (Major)
*   ✅ **Backtesting Engine:** Full historical simulation with fees/slippage (`/backtest`).
*   ✅ **Live Strategy Editor:** Python-based strategy sandbox (`/strategies/editor`).
*   ✅ **Journal Analytics:** "Psychological MRI" and Pattern Analysis.
*   ✅ **Binance Integration:** Multi-broker support including Crypto.
*   ✅ **System Drift Monitor:** Real-time health check (`/analysis/drift`).
*   ✅ **AI Analyst V2:** Doc-RAG, Workflow Engine, BYOK, and **Semantic Summarization**.

##  Inspiration & Examples
*   **Gridbot AI Volatility Harvester:** Check `example/gridbot-ai-volatility-harvester` for frontend UI/UX inspiration.

## 📝 Common Commands
| Action | Command |
| :--- | :--- |
| **Start Full Stack** | `docker compose up --build` |
| **Start Backend Only** | `docker compose up api execution` |
| **Start Frontend Only** | `docker compose up frontend` |
| **Rebuild Specific** | `docker compose up --build <service_name>` |
| **Stop All** | `docker compose down` |
| **Connect to DB** | `docker exec -it postgresql psql -U trader -d mtf_db` |
