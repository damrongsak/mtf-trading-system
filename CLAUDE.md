# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTF Trading System is a spec-driven development (SDD) project that implements a multi-timeframe (MTF) trading system with AI-powered analysis capabilities. The system follows a microservices architecture with Python FastAPI backends, Next.js frontend, and integrates with Google Cloud Vertex AI (Gemini) for LLM-based market analysis.

## Tech Stack

- **Frontend**: Next.js 16 (React 19) with TypeScript, Tailwind CSS
- **Backend**: Python 3.13 + FastAPI microservices
- **Database**: PostgreSQL 15 with pgvector extension
- **Vector Store**: Qdrant for similarity search and pattern matching
- **LLM**: Google Gemini via Vertex AI API
- **Reverse Proxy**: Nginx
- **Containerization**: Docker Compose (dev), targeting GCP Cloud Run/GKE (prod)
- **Package Manager**: pnpm for frontend, uv for backend Python services

## Development Commands

### Docker Compose (Primary Development Method)

```bash
# Start all services
docker compose up --build

# Start specific service
docker compose up api
docker compose up frontend

# Stop all services
docker compose down

# View logs
docker compose logs -f [service-name]
```

### Frontend (Next.js)

```bash
nvm use 22
pnpm install

# Development server (port 3000)
pnpm --filter frontend dev

# Production build
pnpm --filter frontend build

# Start production server
pnpm --filter frontend start

# Lint
pnpm --filter frontend lint
```

### Backend Services

Each Python service (api-gateway, strategy-core, ai-analyst, execution) follows the same structure:

```bash
cd services/[service-name]

# Install uv (first time only)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run with uvicorn (if FastAPI service)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Deployment

```bash
# Deploy to GCP (requires PROJECT_ID environment variable)
./deploy.sh
```

## Architecture

### Service Structure

```
mtf-trading-system/
├─ services/
│  ├─ api-gateway/         # Main FastAPI service, router orchestration
│  ├─ strategy-core/       # MTF/SMC strategy logic, backtesting (vectorbt)
│  ├─ ai-analyst/          # Gemini LLM agent for market analysis
│  └─ execution/           # Trade execution with risk guardrails
├─ frontend/               # Next.js dashboard
├─ specs/                  # YAML/Markdown specs (source of truth)
└─ infra/                  # Infrastructure configs (nginx, etc.)
```

### Spec-Driven Development (SDD) Workflow

This project follows SDD methodology:

1. **Specs First**: All features start with specifications in `/specs/`
   - `01_data_model.yaml`: Define data entities (Candle, Trade, etc.)
   - `02_api_spec.yaml`: OpenAPI contracts for all endpoints
   - Other markdown specs for architecture, AI agent behavior, execution rules

2. **Code from Specs**: Backend routes and models are scaffolded from YAML specs
   - Pydantic models map directly to OpenAPI schemas
   - FastAPI routers implement the contract-first endpoints

3. **Contract Testing**: API contracts defined in specs should drive test generation

### Service Communication

- **Nginx** (port 80): Routes requests to backend API (8000) and frontend (3000)
- **API Gateway** (port 8000): FastAPI service with routers for `/api/v1/signal`, `/api/v1/backtest`
- **Frontend** (port 3000): Next.js app consuming API endpoints
- **PostgreSQL** (internal): Stores structured trade data, OHLCV, strategy runs
- **Qdrant** (port 6333): Vector similarity search for LLM retrieval and pattern matching

### Data Flow

1. Market data ingested from external APIs (Yahoo Finance/Alpaca/Oanda)
2. Stored in PostgreSQL + vectorized features synced to Qdrant
3. Strategy Engine processes signals based on MTF/SMC logic
4. AI Analyst retrieves context from Qdrant and calls Gemini for insights
5. Execution Service validates trades against risk rules ($10 max risk, 0.01 min lot)
6. Results logged to PostgreSQL and displayed in Next.js dashboard

## Key Implementation Details

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `POSTGRES_*`: Database connection settings
- `QDRANT_URL`: Vector store URL
- `GEMINI_API_KEY`: Google Vertex AI API key
- `MIN_LOT`, `MAX_RISK_PER_TRADE`: Execution guardrails

### API Gateway Structure

The FastAPI app (`services/api-gateway/app/main.py`) uses modular routers:
- Import routers from `app/routers/`
- Register with `app.include_router(router, prefix="/api/v1/...")`
- Health check at `/health` endpoint

### Frontend Structure

Next.js 16 app router structure:
- `frontend/app/page.tsx`: Main dashboard page
- `frontend/app/layout.tsx`: Root layout component
- Uses App Router (not Pages Router)

### Reference Implementation
For UI/UX inspiration, check the example project at:
`example/gridbot-ai-volatility-harvester` (Vite + React)

### Database Migrations

Use Alembic for PostgreSQL schema versioning to sync with `specs/01_data_model.yaml`

### Vector Embeddings

When storing trades/candles, generate embeddings via:
- Sentence-transformer models OR
- Gemini Embeddings API
Store in both pgvector (PostgreSQL) and Qdrant for different use cases

## GCP Deployment Strategy

| Component | GCP Service | Notes |
|-----------|-------------|-------|
| PostgreSQL | Cloud SQL | Private VPC connection |
| Docker Images | Artifact Registry | `gcloud builds submit` |
| Backend Services | Cloud Run | Auto-scaling FastAPI instances |
| Secrets | Secret Manager | Gemini API keys, DB credentials |
| Monitoring | Cloud Monitoring | OpenTelemetry integration |
| AI Model | Vertex AI (Gemini 1.5) | Reasoning and retrieval |

## Important Conventions

### Spec-First Development

- **Always check `/specs/` before implementing new features**
- Update YAML specs before writing code
- API contracts in `02_api_spec.yaml` drive Pydantic model generation
- Keep specs and implementation in sync

### Service Isolation

- Each microservice has its own Dockerfile
- Services communicate via HTTP APIs (no direct DB sharing)
- Use Pydantic models for data validation and serialization

### Risk Management

The execution service enforces strict guardrails:
- Maximum risk per trade: $10 (configurable via `MAX_RISK_PER_TRADE`)
- Minimum lot size: 0.01 (configurable via `MIN_LOT`)
- Risk calculation: `lot = risk_usd / sl_distance_usd`

### Testing Strategy

- Pytest for Python services (run with `uv run pytest`)
- Contract tests derived from OpenAPI specs
- Backtest validation using vectorbt
- Frontend testing with Playwright

## Project GCP ID

The `deploy.sh` script uses GCP project ID: `line-bot-2b383`
