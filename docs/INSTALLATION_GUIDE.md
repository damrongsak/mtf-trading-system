# MTF Olympus: Professional Installation & Setup Guide

This guide provides step-by-step instructions for an initial project setup or a fresh installation of the **MTF Olympus (v2.1)** trading system.

## 📋 Prerequisites

Ensure your environment meets the following requirements:
- **OS**: Linux (Ubuntu 22.04+ recommended) or WSL2.
- **Docker**: Docker Engine 24.0+ and Docker Compose v2.20+.
- **Node.js**: v22 (managed via `nvm`).
- **Python**: v3.13+ (dependencies managed via `uv`).
- **Tools**: `pnpm` (for frontend), `curl`, `git`.

---

## 🛠️ Step 1: Environment Configuration

Clone the repository and prepare your environment variables.

```bash
# Clone the repository
git clone <repository-url> mtf-trading-system
cd mtf-trading-system

# Create environment file
cp .env.example .env
```

### Essential Environment Variables
Edit the `.env` file with your credentials:
- `OANDA_API_KEY` & `OANDA_ACCOUNT_ID`: For OANDA integration.
- `CTRADER_CLIENT_ID` & `CTRADER_CLIENT_SECRET`: For cTrader Open API.
- `GEMINI_API_KEY`: For AI Analyst features (Google Vertex AI).
- `DATABASE_URL`: `postgresql://trader:trader@mtf-postgres:5432/mtf_db`

---

## 🏗️ Step 2: Infrastructure & Database Initialization

MTF Olympus uses **Spec-First Migration (SFM)**. The `data-pipeline` service is the Single Migration Authority.

### 1. Start Core Infrastructure
```bash
docker compose up -d mtf-postgres mtf-redis qdrant
```

### 2. Apply Database Migrations
Run Alembic from the `data-pipeline` container to create the schema defined in `specs/03_data_model.yaml`.
```bash
docker compose exec data-pipeline alembic upgrade head
```

### 3. Seed Production Data
Initialize system configs, users (admin, trader1, trader2), market symbols, and risk rules.
```bash
docker compose exec api-gateway uv run python scripts/production_init.py
```

---

## 🚀 Step 3: Service Orchestration

### Method A: Full Stack (Recommended for Production/Demo)
```bash
docker compose up --build -d
```

### Method B: Selective Startup (Development)
```bash
# Start backend services
docker compose up -d api-gateway strategy-core data-pipeline execution ai-analyst

# Start frontend locally (faster for UI dev)
nvm use 22
pnpm install
pnpm --filter frontend dev
```

---

## 🛡️ Step 4: Verification & Health Checks

Verify that the installation is successful and services are interconnected.

### 1. Schema Verification
Confirm code models and database are in perfect sync.
```bash
docker compose exec api-gateway uv run python scripts/verify_schema.py
```

### 2. Service Connectivity
Check the health status of all APIs.
```bash
# API Gateway Health
curl http://localhost:8000/health

# Gap Discovery (Verify data integrity logic)
docker compose exec data-pipeline curl http://localhost:8000/api/v1/discovery/gaps?days=1
```

---

## 📚 Key Development Commands

| Action | Command |
| :--- | :--- |
| **View Logs** | `docker compose logs -f <service_name>` |
| **Stop All** | `docker compose down` |
| **Rebuild Single Service** | `docker compose build <service_name> && docker compose up -d <service_name>` |
| **Run Tests** | `docker compose exec <service_name> uv run pytest` |

## ⚠️ Important Rules (Spec-Driven Development)
1. **Never modify implementation without updating specs**: All changes must start in the `specs/` directory.
2. **Execution Guardrails**: The hot path is DB-free. Persistence is handled asynchronously.
3. **Model Authority**: Always sync `api-gateway` models with `data-pipeline` (the authority).

---
*Last Updated: 2026-03-07*
