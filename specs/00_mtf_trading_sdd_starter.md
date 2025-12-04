# MTF Trading System — SDD Starter Repo

This repository scaffold implements a Spec-Driven Development starter for the MTF + SMC trading system you described. It contains specs, service placeholders, Docker compose, CI/deploy helpers, and VS Code Cloud Code configuration so you can open the workspace and start implementing with contract-first flow.

---

## Repo layout (tree)

```
mtf-trading-system/
├─ README.md
├─ docker-compose.yml
├─ deploy.sh
├─ .env.example
├─ .cloudcode/
│  └─ cloudbuild.yaml
├─ specs/
│  ├─ 00_architecture.md
│  ├─ 01_data_model.yaml
│  ├─ 02_api_spec.yaml
│  ├─ 03_ai_agent_spec.md
│  ├─ 04_execution_rules.md
│  └─ 05_testing_plan.md
├─ services/
│  ├─ api-gateway/
│  │  ├─ Dockerfile
│  │  └─ app/
│  │     ├─ main.py
│  │     ├─ routers/
│  │     │  ├─ signal.py
│  │     │  └─ backtest.py
│  │     └─ models/
│  │        └─ pydantic_models.py
│  ├─ strategy-core/
│  │  ├─ Dockerfile
│  │  └─ app/
│  │     └─ strategy.py
│  ├─ ai-analyst/
│  │  ├─ Dockerfile
│  │  └─ app/
│  │     └─ agent.py
│  └─ execution/
│     ├─ Dockerfile
│     └─ app/
│        └─ executor.py
├─ frontend/
│  ├─ package.json
│  ├─ next.config.js
│  └─ app/
│     └─ page.tsx
└─ infra/
   └─ nginx/
      └─ default.conf
```

---

## Quick start (VS Code + Cloud Code)

1. Install VS Code + Cloud Code extension.
2. Clone this repo into your workspace.
3. Open the folder in VS Code. Cloud Code will detect `docker-compose.yml` and suggest a run/debug configuration.
4. Copy `.env.example` to `.env` and fill secrets (Postgres password, Gemini key, Qdrant URL).
5. Run `docker compose up --build` from VS Code Cloud Code or terminal.

---

## Key files (boilerplate snippets)

### docker-compose.yml
```yaml
version: '3.9'
services:
  nginx:
    image: nginx:latest
    volumes:
      - ./infra/nginx/default.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - api
      - frontend

  api:
    build: ./services/api-gateway
    env_file: .env
    ports:
      - "8000:8000"
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
    image: qdrant/qdrant:latest
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

### .env.example
```
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader
POSTGRES_DB=mtf_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
QDRANT_URL=http://qdrant:6333
GEMINI_API_KEY=
MIN_LOT=0.01
MAX_RISK_PER_TRADE=10
```

### services/api-gateway/Dockerfile
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY services/api-gateway/app /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic psycopg[binary] sqlalchemy asyncpg
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### services/api-gateway/app/main.py
```python
from fastapi import FastAPI
from routers import signal, backtest

app = FastAPI(title="MTF Trading API")
app.include_router(signal.router, prefix="/api/v1/signal")
app.include_router(backtest.router, prefix="/api/v1/backtest")

@app.get("/health")
async def health():
    return {"status":"ok"}
```

### services/api-gateway/app/routers/signal.py
```python
from fastapi import APIRouter
from pydantic_models import SignalRequest, SignalResponse

router = APIRouter()

@router.post("/check")
async def check_signal(req: SignalRequest) -> SignalResponse:
    # Contract-first: implement logic to call strategy-core service
    return SignalResponse(allowed=False, reason="not implemented")
```

### services/strategy-core/app/strategy.py
```python
# Placeholder: vectorbt-based backtest & MTF resampling will live here

def run_backtest(config, data_df):
    # - resample
    # - compute indicators
    # - simulate trades
    return {"summary": "not implemented"}
```

### services/ai-analyst/app/agent.py
```python
# Placeholder for Gemini agent interaction

def analyze(context: dict) -> dict:
    # - retrieve embeddings from Qdrant
    # - call Gemini (Vertex AI) with structured prompt
    return {"insight": "not implemented"}
```

### services/execution/app/executor.py
```python
# Execution guardrails

def can_execute(risk_usd: float, sl_distance_usd: float, min_lot: float) -> bool:
    lot = risk_usd / sl_distance_usd if sl_distance_usd>0 else 0
    return lot >= min_lot
```

### frontend/app/page.tsx
```tsx
export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">MTF Trading Dashboard (placeholder)</h1>
      <p>Open /specs to follow the Spec-Driven Development flow.</p>
    </main>
  )
}
```

### specs/01_data_model.yaml (example)
```yaml
entities:
  Candle:
    fields:
      - name: timestamp
        type: datetime
      - name: open
        type: float
      - name: high
        type: float
      - name: low
        type: float
      - name: close
        type: float
      - name: volume
        type: float

  Trade:
    fields:
      - name: id
        type: uuid
      - name: strategy_name
        type: string
      - name: entry_price
        type: float
      - name: sl_price
        type: float
      - name: tp_price
        type: float
      - name: lot
        type: float
      - name: pnl
        type: float
```

### specs/02_api_spec.yaml (snippet)
```yaml
openapi: 3.0.0
info:
  title: MTF Trading API
  version: 0.1.0
paths:
  /api/v1/signal/check:
    post:
      summary: Check if a signal is valid given current state
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SignalRequest'
      responses:
        '200':
          description: signal check response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SignalResponse'
components:
  schemas:
    SignalRequest:
      type: object
      properties:
        symbol:
          type: string
        timeframe:
          type: string
    SignalResponse:
      type: object
      properties:
        allowed:
          type: boolean
        reason:
          type: string
```

### .cloudcode/cloudbuild.yaml
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/mtf-api', './services/api-gateway']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/mtf-api']
images:
  - 'gcr.io/$PROJECT_ID/mtf-api'
```

### deploy.sh
```bash
#!/usr/bin/env bash
# Minimal deploy script: build and push images to Artifact Registry then deploy to Cloud Run
set -e
PROJECT_ID=${PROJECT_ID:-your-gcp-project}
IMAGE=gcr.io/$PROJECT_ID/mtf-api

docker build -t $IMAGE ./services/api-gateway
docker push $IMAGE
# Example: gcloud run deploy mtf-api --image $IMAGE --region=asia-southeast1 --platform=managed
```

---

## Implementation suggestions & priorities
1. Start with `specs/02_api_spec.yaml` and implement the API contract in `services/api-gateway` using the Pydantic models defined in `specs`.
2. Implement `execution` guardrails next (very small, high-value module).
3. Add `strategy-core` backtest harness (vectorbt) as a worker service behind Celery.
4. Integrate Qdrant & pgvector: store embeddings in both, use Qdrant for fast retrieval.
5. Implement `ai-analyst` last: build retrieval + prompt templates + Gemini calls.

---

## What I can generate next (choose one):
- Full Vectorbt backtest notebook (Python) wired to this repo structure.
- Production-ready `execution` module (TypeScript or Python) with unit tests and contract tests.
- Full FastAPI router implementations from `specs/02_api_spec.yaml` with Pydantic models and Alembic migrations.
- Next.js 15 dashboard scaffold with a couple of pages and API hooks.

Pick one and I will generate the code for it right away and add it into this repo scaffold.

---

Happy to iterate — once you pick the next target I will produce the full implementation for that module. Let's build something that refuses to lose money (politely).

