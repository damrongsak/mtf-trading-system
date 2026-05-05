# GEMINI.md — Unified AI Operational Spec (v3.0)

**MTF Olympus** is a distributed quantitative trading system. This document is the **Single Source of Truth** for methodology. Any AI agent working on this project MUST adhere to the protocols defined here.

---

## 🛡️ PHASE 0: Cold Start Protocol (Session Alignment)
Before starting ANY task in a new session, the agent MUST perform these three steps:

1.  **Read This Document**: Acknowledge the guardrails below.
2.  **Verify System Health**: Run the health check script.
    ```bash
    docker compose exec api-gateway python scripts/system_health_check.py
    ```
3.  **Reality Anchor (V2.5)**: If the task involves market data or logic, fetch the current price from Redis.
    ```bash
    # Check Spot Price (XAUUSD Example)
    docker compose exec api-gateway redis-cli get market_data:spot:XAUUSD
    ```
4.  **Institutional Regime**: Verify the current GEX regime for context.
    ```bash
    docker compose exec api-gateway python scripts/update_regime_monitor.py
    ```
5.  **Historical Anchor**: Use `get_regime_history` tool to verify historical bias consistency before high-risk analysis.

---

## 🛠️ PHASE 1: Spec-Driven Development (SDD)
**The Spec is the Source of Truth. Do not write implementation code without updating and validating specs first.**

### 🛑 Mandatory Guardrails
1.  **No Implementation without Spec**: You MUST NOT modify Python/React code until the corresponding `.yaml` or `.md` spec in `specs/` is updated.
2.  **Hierarchy of Truth**: Root `specs/*.yaml` files supersede any subdirectories.
    - Authoritative Data Model: `specs/03_data_model.yaml`
    - Authoritative API: `specs/04_api_spec.yaml`
3.  **Single Migration Authority**: The `data-pipeline` service is the **Source of Truth** for database schemas. ALL changes MUST be applied via **Alembic** in `services/data-pipeline`. Manual SQL scripts are strictly prohibited.
4.  **Planning Mode**: Always create or update an `implementation_plan.md` that explicitly lists the spec changes.
5.  **🚫 Never Auto-Commit**: You MUST NOT run `git commit` or `git push` autonomously. Present staged changes to the user first.

### 🛠️ SDD Workflow Steps
1.  **Identify**: Determine if the change affects Data Models (`03`), API Contracts (`04`), or Logic (`01`/`08`).
2.  **Update Root Spec**: Modify the master file in the `specs/` directory.
3.  **Generate Code**:
    - **Backend**: `docker compose exec api-gateway /venv/bin/bash scripts/gen_backend.sh`
    - **Frontend**: `cd frontend && pnpm run gen:api`
4.  **Implement**: Follow Clean Code principles and the verification gates below.

---

## 🛡️ PHASE 2: Quality Gates (Zero-Defect Standard)
Before finalizing any task, the agent MUST pass these four gates:

| Gate | Verification Method | Command |
| :--- | :--- | :--- |
| **Logic** | 100% pass rate in `pytest` | `uv run pytest` |
| **Quality** | Zero errors in `ruff` | `ruff check .` |
| **Schema** | No DDL drift | `docker compose exec api-gateway python scripts/verify_api_schemas.py` |
| **Institutional** | cTrader/Order conformity | `docker compose exec api-gateway python scripts/verify_ctrader_standards.py` |

---

## 🛠️ PHASE 3: Institutional Tool Standards
All AI tools (in `ai-analyst`) MUST adhere to these resilience standards:
1.  **Inherit from `BaseTool`**: Must use `app.core.base_tool.BaseTool`.
2.  **Implement `run_tool`**: No `_run` or `_arun`. Use `async def run_tool(self, input_data, auth_token, **kwargs)`.
3.  **Scaffold First**: Use the scaffolding script to create new tools:
    ```bash
    docker compose exec ai-analyst python scripts/scaffold_tool.py --name "ToolName"
    ```
4.  **🚫 No Reentrant Calls**: Never call the `api-gateway` from an internal service tool. Use Direct Service Calls or Redis (ECST).

---

## 🏗️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (React 19) | Modern dashboard |
| **API Gateway** | Python (FastAPI, Redis) | Auth, Routing, ECST Cache |
| **Execution** | Python (Async Worker) | Resilient trade lifecycle |
| **Data Pipeline** | Python (StreamManager) | Real-time CME/Oanda streams |
| **Database** | PostgreSQL 15 | Relational data & JSONB models |
| **Messaging** | Redis Streams | Event Bus / Messaging backbone |

### 📁 Directory Structure
- `specs/`: **Source of Truth**. Architecture (`01`), Models (`03`), API (`04`), Rules (`08`).
- `services/`: Microservices (`api-gateway`, `strategy-core`, `ai-analyst`, `execution`).
- `scripts/`: Verification and utility scripts.
- `master_data/`: Versioned system configurations (JSON).

---

## 🔑 Key Domain Logic & Constraints
- **Lot Scaling**: All broker units scaled via **100,000.0** divisor (1,000 units = 0.01 lots).
- **Absolute Units**: Always use positive `units` + explicit `side` (`BUY`/`SELL`).
- **cTrader IDs**: `orderId` for Pending; `positionId` for Filled. Use `broker_trade_id` for stable mapping.
- **HFT-lite Path**: Execution path is **DB-free**. Uses Redis Streams and in-memory caches.
- **GEX V2.5**: Must provide `spot_price` for reality-anchoring. Default aggregation = **90-Day DTE**.
- **Regime Synchronization**: Institutional regimes are synced to the **H4 timeframe** (Rule 5.6.3).
- **Strike-level Greeks**: `open_interest` data must be stored with per-strike Greeks (Delta, Gamma, Vanna, Charm) to enable second-order risk analysis.

---

## 📝 Common Operational Commands
| Action | Command |
| :--- | :--- |
| **Start Backend** | `docker compose up api execution strategy-core` |
| **Verify Schema** | `docker compose exec api-gateway python scripts/verify_api_schemas.py` |
| **Export/Import MDMS** | `docker compose exec api-gateway python scripts/manage_master_data.py [export/import]` |
| **Update Regime Monitor** | `docker compose exec api-gateway python scripts/update_regime_monitor.py` |
| **Check Regime History** | `curl -X GET http://localhost:8000/api/v1/analysis/gamma/regime-history?symbol=XAUUSD` |
| **Reload Strategies** | `curl -X POST http://localhost:8000/api/v1/strategies/reload` |

---
**MTF Olympus** | *Spec-Driven Methodology*
