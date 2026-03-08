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
| **API Gateway** | Python (FastAPI, Redis) | Auth (JWT), routing, and **ECST Cache** for market symbols. |
| **Strategy Core** | Python (Vectorbt, Pandas) | Implements Logic and **Async Execution Client** (Redis Queue). |
| **Execution Service** | Python (Async Worker, Redis) | **Resilient Background Worker** for trade lifecycle & Risk. |
| **AI Analyst** | Python (LangGraph, Gemini 2.5) | "Market Observer" Agent and RAG-based Journal analysis. |
| **Data Pipeline** | Python (StreamManager, Oanda) | Real-time streams and **Symbol Details event broadcasting**. |
| **Database** | PostgreSQL 15 | Stores relational trade data and **Cached Symbol Metadata (JSONB)**. |
| **Vector Store** | Qdrant | Handles similarity search for pattern recognition and RAG. |
| **Infrastructure** | Redis, Docker, Nginx | Messaging backbone, container orchestration, and proxying. |
| **Cloud Target** | GCP (Cloud Run, SQL) | Production environment. |

### 🛠️ Decoupled Architecture (v2.1+)
The system utilizes two primary patterns for high resilience:
1.  **Event-Carried State Transfer (ECST)**: `data-pipeline` broadcasts symbol metadata which is cached locally by `api-gateway`.
2.  **Asynchronous RPC**: `strategy-core` pushes trade commands to a Redis queue, processed asynchronously by the `execution` worker.

### 📂 Directory Structure
*   `specs/`: **Source of Truth**. Contains Architecture (`01`), Data Models (`03`), API Contracts (`04`), and Logic Rules (`08`).
*   `services/`: Backend microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `execution`, `data-pipeline`).
*   `frontend/`: Next.js web application.
*   `infra/`: Infrastructure configurations (Nginx, etc.).
*   `docker-compose.yml`: Orchestration for local development.

## 🛠️ Development Workflow

### 1. The SDD Process (STRICT ENFORCEMENT)
**The Spec is the Source of Truth. Do not write implementation code without updating and validating specs first.**

#### 🛑 AI Agent Guardrails
1.  **NO IMPLEMENTATION without SPEC**: You MUST NOT modify Python/React code until the corresponding `.yaml` or `.md` spec in `specs/` is updated.
2.  **SEARCH FOR DUPLICATES**: Before editing a spec, search the codebase for duplicate files (e.g., `04_api_spec.yaml` lurking in subdirectories). **Delete duplicates immediately.**
3.  **VALIDATE SCHEMA**: After updating a spec, run the appropriate generation script (`scripts/gen_backend.sh` or `pnpm run gen:api`) and verify results.
4.  **PLANNING MODE**: Always create or update an `implementation_plan.md` that explicitly lists the spec changes.
5.  **🚫 NEVER AUTO-COMMIT**: You MUST NOT run `git commit` or `git push` autonomously. Always present the staged changes and commit message to the user first, and **wait for explicit approval** before executing any git commit command. No exceptions.
6.  **📋 SPEC CHECK BEFORE CODE CHANGE**: Before editing, inserting, or fixing ANY code (Python, TypeScript, SQL, config), you MUST first:
    - Identify which spec(s) in `specs/` are affected (Data Model `03`, API Contract `04`, Architecture `01`, Logic `08`).
    - State the spec impact explicitly to the user (e.g., "This change affects `04_api_spec.yaml` endpoint X").
    - Update the spec **before** touching the implementation code.
    - If the change is a pure bugfix with no spec impact, explicitly state "No spec impact" and explain why.
7.  **⚡ HFT-Lite Hot Path Protection**: The Execution Service hot path (order placement → fill → publish) is **DB-free by design**. It must use only:
    - **L3 In-Memory Cache** (`_symbol_cache`) for symbol resolution — O(1), no I/O.
    - **Redis Pub/Sub** (`fill_publisher`) for fill events — non-blocking.
    - **NO PostgreSQL writes** inside the hot path. Any DB persistence (e.g., `_save_filled_trade_to_db`) MUST be:
      - Decoupled via **Redis Stream** (`execution.filled.stream`) consumed by a separate worker.
      - Or explicitly delayed as a truly detached background task that cannot block `await` on the fill path.
    - Violating this rule adds **10–100ms DB latency per trade** — unacceptable for live execution.
    - ⚠️ **Current known issue**: `_save_filled_trade_to_db()` in `ctrader.py` uses `asyncio.create_task()` (non-blocking at call site) but the task itself performs an async PostgreSQL write (`AsyncSessionLocal`). Under high DB load this can steal event loop time. The correct fix is to publish the fill to `execution.filled.stream` and let the worker process DB writes asynchronously. Refactor is pending.
8.  **📚 READ PROJECT DOCS FIRST**: Before starting any task, read the relevant quick-reference docs:
    - `docs/AI_AGENT_GUIDE.md` — HFT-lite hot path, tool definitions, Redis key conventions.
    - `docs/database_schema.md` — ERD and table relationships.
    - `docs/STRATEGY_DEV_GUIDE.md` — Strategy plugin architecture.
    - `docs/PLUGIN_DEV_GUIDE.md` — Plugin lifecycle hooks.
    - `specs/04_api_spec.yaml` — API contract (source of truth for endpoints).
    - `specs/03_data_model.yaml` — Data model (source of truth for schemas).
    - Do NOT assume knowledge of the system. Always verify against these docs before proposing changes.
9.  **🛠️ Infrastructure Guardrails (CRITICAL)**:
    - **NO `command` OVERRIDE**: Do NOT use the `command` field in `docker-compose.yml` for infrastructure services like `redis` or `mtf-postgres`. Overriding the command can prevent critical modules (e.g., RediSearch, RedisJSON) from loading.
    - **Use `REDIS_ARGS` / `POSTGRES_INITDB_ARGS`**: If you need to tune parameters like `--maxmemory`, use the designated environment variables supported by the official images. This ensures the default entrypoint can still initialize required extensions.
    - **Single Point of Configuration**: Maintain total memory allocation within the 8GB RAM host limit (Docker target: ~6.5GB).

#### 🛠️ SDD Workflow Steps
1.  **Identify Change**: Determine if the change affects Data Models (`03`), API Contracts (`04`), or Logic/Architecture (`01`/`08`).
2.  **Update Root Spec**: Modify the master file in the `specs/` directory.
3.  **Generate Code**:
    *   **Backend**: `docker compose exec api-gateway /venv/bin/bash scripts/gen_backend.sh`
    *   **Frontend**: `cd frontend && pnpm run gen:api`
4.  **Implement & Verify**: Finalize implementation and run contract tests (`uv run pytest`).

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

*   **Diagnosing Environment Issues:**
    If `node` or `npm` commands are missing in non-interactive shells/scripts:
    1.  Check OS & Node: `uname -a && node -v`
    2.  Locate NVM: `ls -la ~/.nvm/nvm.sh`
    3.  **Fix:** Explicitly source NVM before running commands:
        ```bash
        source ~/.nvm/nvm.sh && npm run lint
        ```

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

### 4. Database Migration Standard (World-Class SDD)
To prevent schema drift across microservices, MTF Olympus follows a **Spec-First Migration (SFM)** pattern:

1.  **Single Source of Truth**: All schema changes MUST be defined in `specs/03_data_model.yaml` first.
2.  **Migration Authority**: The `data-pipeline` service acts as the **Migration Authority**. All `alembic` commands to evolve the shared `mtf_db` should be run from this service.
3.  **Full Model Synchronization**: `data-pipeline` MUST contain the **full, authoritative SQLAlchemy models** (copied from `api-gateway` or `strategy-core`). **STUB MODELS ARE FORBIDDEN** as they cause Alembic to generate destructive `DROP` operations for missing fields.
4.  **Cross-Service Sync**: Other services must not create conflicting migrations. They should consume the schema by aligning their `models.py` with the root spec.
5.  **Verification**: Before deployment, run the schema validator. Note: The validator in `api-gateway` is configured to load and verify against `data-pipeline`'s context:
    ```bash
    docker compose exec api-gateway uv run python scripts/verify_schema.py
    ```
6.  **Emergency Fixes**: If a manual DDL fix (e.g., `ALTER TABLE`) is required, it must be documented and back-ported to the root `03_data_model.yaml` immediately to maintain SDD integrity.

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
*   ✅ **AI Analyst V2:** Doc-RAG, Workflow Engine, BYOK, **Semantic Summarization**, and **Universal Agents (MCP)**.
*   ✅ **Decoupled Architecture (v2.1):** Implemented **ECST** for symbol metadata and **Async RPC** for resilient execution.
*   ✅ **Quality Assurance:** Comprehensive Unit Test Suite with **>60% code coverage** verified across all backend services.

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
| **Verify DB Schema** | `docker compose exec api-gateway uv run python scripts/verify_schema.py` |
