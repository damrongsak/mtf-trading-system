## ⚙️ Core System Overview

| Layer                                | Tech                                                                    | Purpose                                                                   |
| ------------------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Frontend (UI)**                    | Next.js 15 (React 19)                                                   | Trading dashboard, signals view, trade logs, and scenario simulator       |
| **API Gateway / Reverse Proxy**      | Nginx (Dockerized)                                                      | Routing to Python microservices & static assets                           |
| **Backend (Core)**                   | Python 3.13 + FastAPI (+ Celery for async jobs)                         | Strategy logic, data processing, orchestration, API endpoints             |
| **Database**                         | PostgreSQL 15 + pgvector                                                | Structured trade data, historical prices, embeddings                      |
| **Vector Store**                     | Qdrant                                                                  | Fast similarity search (for LLM retrieval & pattern matching)             |
| **LLM Agent Layer**                  | Gemini (via Google Cloud Vertex AI API)                                 | Natural-language reasoning, market narrative analysis, strategy synthesis |
| **Containerization / Orchestration** | Docker Compose → later GCP Cloud Run / GKE                              | Isolation, CI/CD, scaling                                                 |
| **Infrastructure**                   | Google Cloud (Cloud SQL, Artifact Registry, Secret Manager, Monitoring) | Deployment, monitoring, secrets, CI/CD                                    |
| **Dev Workflow**                     | VS Code + Cloud Code extension                                          | Spec writing, service scaffolding, debugging, deployment                  |
| **Documentation**                    | Markdown SDD Specs + OpenAPI (auto-generated)                           | One source of truth for API & architecture                                |

---

## 🧩 Spec-Driven Development Flow (SDD)

SDD means: **you define behavior and data contracts first**, then implement code to satisfy them.

### 1. Specification Structure

Keep your specs inside `/specs/`:

```
/specs/
 ├─ 00_architecture.md
 ├─ 01_data_model.yaml
 ├─ 02_api_spec.yaml
 ├─ 03_ai_agent_spec.md
 ├─ 04_execution_rules.md
 └─ 05_testing_plan.md
```

Each spec drives its counterpart in `/services/`:

* `/services/trading/`
* `/services/ai-agent/`
* `/services/data-pipeline/`
* `/frontend/` (Next.js)

Example:
If you define `GET /api/v1/signal` in `02_api_spec.yaml`, FastAPI autogenerates that route stub with `@router.get("/signal")`.
Then you “fill the function” — Cloud Code helps you scaffold directly from spec.

---

## 🧠 Suggested Modules

### A. Trading Data Pipeline

* Source: Yahoo Finance / Alpaca / Oanda API
* Ingest → PostgreSQL (OHLCV)
* Vectorize features (ATR, EMA, candle embeddings) and sync to Qdrant for clustering or similarity lookup.

### B. Strategy Engine (Service: `strategy-core`)

Implements:

* MTF/SMC logic (from your PDF system)
* Parameter registry in PostgreSQL
* Backtest via Vectorbt (run headless job in Celery worker)
* Result storage + visualization via API

### C. LLM Agent (Service: `ai-analyst`)

* Input: news, charts, strategy logs
* Prompt Gemini: “analyze last 24h volatility shift given our signals”
* Retrieve knowledge base from Qdrant
* Output structured insight JSON (can be consumed by frontend)

### D. Execution Service

* Risk engine guardrails ($10 cap, min lot 0.01)
* Trade simulation or live connector (CCXT)
* Logging → PostgreSQL

---

## 🪶 Folder & Container Layout

```
mtf-trading-system/
│
├─ docker/
│   ├─ nginx/
│   │   └─ default.conf
│   ├─ postgres/
│   └─ qdrant/
│
├─ services/
│   ├─ api-gateway/        # FastAPI root service
│   ├─ strategy-core/
│   ├─ ai-analyst/
│   └─ execution/
│
├─ frontend/               # Next.js 15 app
│
├─ specs/
│
├─ docker-compose.yml
└─ .cloudcode/             # Cloud Code configs
```

---

## 🧰 Dev Environment Setup

**docker-compose.yml** example skeleton:

```yaml
version: '3.9'
services:
  nginx:
    image: nginx:latest
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - api
      - frontend

  api:
    build: ./services/api-gateway
    env_file: .env
    depends_on:
      - postgres
      - qdrant

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: trader
      POSTGRES_DB: mtf_db
    volumes:
      - pgdata:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

volumes:
  pgdata:
  qdrant_storage:
```

---

## 🧩 Google Cloud Integration Plan

| Component         | GCP Service            | Notes                            |
| ----------------- | ---------------------- | -------------------------------- |
| Postgres DB       | Cloud SQL              | link via private VPC             |
| Docker images     | Artifact Registry      | `gcloud builds submit`           |
| Backend deploy    | Cloud Run              | auto-scale FastAPI microservices |
| Secrets           | Secret Manager         | store Gemini API keys            |
| Logging & Metrics | Cloud Monitoring       | integrate with OpenTelemetry     |
| AI Model          | Vertex AI (Gemini 1.5) | retrieval + reasoning agent      |

---

## 🔍 Recommendations & Enhancements

1. **Schema versioning** — use `alembic` for PostgreSQL migrations to sync your SDD data models.
2. **Inter-service contracts** — enforce using Pydantic models exported from specs.
3. **Embedding flow** — when saving trades, generate embeddings (sentence-transformer / Gemini Embeddings) → store to pgvector and Qdrant.
4. **Observability** — add Prometheus + Grafana stack early; visualize latency, drawdown, Sharpe over time.
5. **Testing** — Pytest + Playwright (for frontend) + contract tests from SDD YAML.
6. **Workflow automation** — use n8n or Airflow to schedule retraining, data refresh, or prompt evaluation.
7. **CI/CD** — GitHub Actions with `gcloud` CLI to deploy on merge; run unit + vectorized backtest tests.

---

## 🧭 Next Step

You can start with this Spec-Driven sequence:

1. `00_architecture.md` — describe above stack in your own context.
2. `01_data_model.yaml` — define all data entities (Trade, Candle, StrategyRun, RiskRule).
3. `02_api_spec.yaml` — design API routes for `/signal`, `/backtest`, `/risk/check`, `/agent/analyze`.
4. `03_ai_agent_spec.md` — define Gemini agent behaviors, prompt schema, retrieval method.
5. Scaffold `/services/api-gateway` using Cloud Code from these specs.

---
With this foundation, you’re set to build a robust multi-agent trading intelligence system that leverages the best of modern tech and AI capabilities. Happy coding! 🚀