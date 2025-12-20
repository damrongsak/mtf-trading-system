# MTF Trading System — Spec Driven Development (SDD) Checklist

This document translates the complete multi-dimensional trading system blueprint into an **SDD-based implementation checklist**, following the structured methodology described in the uploaded *Spec Driven Development (SDD)* reference. filecite30†Spec Driven Development (SDD).md

---

## 0. SDD Core Philosophy

- **Specification as Source of Truth** — All system behavior, APIs, and data models originate from `/specs` files. The codebase reflects, not defines, intent.
- **Intent-First Development** — Define the “why” and “what” before the “how.” Each spec becomes an executable contract.
- **Task Granularity** — Every implementation item must be specific, measurable, and testable.
- **Validation in Phases** — Each SDD phase (Specify → Plan → Tasks → Implement) includes a checkpoint for verification.

---

## 1. Core Specification Files (/specs)
| File | Description | Purpose (SDD Phase 1) |
| :--- | :--- | :--- |
| `01_architecture.md` | System overview: Data pipeline, strategy, execution, AI agent, API Gateway. | Defines **service boundaries** and data flow. |
| `03_data_model.yaml` | Entity definitions: `Candle`, `Trade`, `StrategyRun`, `RiskRule`, `AgentInsight`. | Defines the **PostgreSQL schema** and Pydantic models. |
| `04_api_spec.yaml` | OpenAPI contract for all routes: `/signal`, `/backtest`, `/risk/check`, `/exec/simulate`. | Defines the **API contracts** for the `api-gateway`. |
| `06_ai_agent.md` | Prompt schema, Qdrant retrieval pipeline, output JSON format for Gemini reasoning. | Defines the **LLM agent's contract**. |
| `08_execution_rules.md` | **Critical Rules**: $10 Max Risk Cap, Min Lot 0.01 Rejection, ATR/CKS Stop logic, 4H/D EMA Filter. | Defines the **core guardrails** for the `execution` service. |
| `09_testing_plan.md` | Unit, Contract, Integration, Regression (fixed seed backtest), and E2E strategy. | Ensures **mandatory testing** for each implementation step. |

---

## 2. Implementation Phases (SDD Process)

| Phase | Goal | Acceptance Checkpoint |
| :--- | :--- | :--- |
| **1. Specify** (Weeks 1-2) | Define *what* and *why* (Architecture, Data, Rules). | All `/specs` files are validated (e.g., OpenAPI linting, Schema review). |
| **2. Plan** (Weeks 2-3) | Define technical *how* (Stack, Infrastructure). | Infrastructure diagram approved (GCP Cloud Run, Cloud SQL private IP, CI/CD design). |
| **3. Tasks** (Weeks 3-5) | Break specs into actionable, small, testable tasks. | Task list is critically reviewed for **omissions/edge cases** (e.g., market holiday handling). |
| **4. Implement** (Weeks 5+) | Implement, focusing on one task at a time. | Code output is reviewed against the **task's defined acceptance criteria**. |

---

## 3. Module Checklists

### **A. Data Pipeline (Service: `data-pipeline`)**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| Create `Candle` table migration | Able to ingest CSV of candles and query by timeframe | Alembic + ingestion test |
| Implement OHLCV loader | Returns DataFrame with timezone-aware timestamps | Unit test with fixture CSV |
| Implement resampling util (15m→1H→4H→D) | No lookahead; resample deterministic | Deterministic resample test |
| Embedding job to Qdrant/pgvector | Embeddings stored and retrievable | Mock embedding + retrieval test |

### **B. Execution / Risk (Service: `execution`) — Start here**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| Guardrail logic (`can_execute`) | Rejects trades where lot < 0.01; outputs reason | Boundary tests (min lot, zero/negative) |
| `/risk/check` API route | Returns JSON with execution decision | Contract test (OpenAPI match) |
| `/exec/simulate` endpoint | Records trade as `simulated`, PnL=0 | DB integration test |
| `pre_trade_kill_switch` | Blocks execution when drawdown > threshold | Simulated drawdown test |

### **C. Strategy Core (Service: `strategy-core`)**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| MTF indicator engine (EMA, ATR, BOS/ChoCH) | Aligned 15m outputs without lookahead | Compare vs reference library |
| SMC detectors (Order Block, FVG) | Detects zones with timestamps + score | Unit tests with crafted data |
| Vectorbt backtest wrapper | Deterministic output summary + trade list | Fixed seed smoke test |

### **D. AI Analyst (Service: `ai-analyst`)**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| Define Gemini prompt schema | Output includes `insight_type`, `confidence`, `summary` | JSON schema validation |
| Implement Qdrant retrieval flow | Top-k contextual retrieval within token budget | Mock retrieval test |
| Gemini API wrapper | Handles retries and rate limits | Mock API test |

### **E. API Gateway (Service: `api-gateway`)**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| Implement routers per `04_api_spec.yaml` | OpenAPI validates routes | Contract test |
| Implement shared Pydantic models | Round-trip serialization works | Serialization test |

### **F. Frontend (Next.js 15)**
| Task | Acceptance Criteria | Test |
|------|----------------------|------|
| Scaffold pages `/signals`, `/trades`, `/backtests`, `/agent` | API-connected and renders mock data | Playwright navigation test |
| React hooks for API (`useSignalCheck`, `useBacktestRun`) | Hook returns expected states | React Testing Library test |

---

## 4. CI/CD & Cloud Infrastructure
| Component | Requirement |
|------------|-------------|
| **GitHub Actions** | Linting, unit tests, Docker build/push to Artifact Registry |
| **Cloud Build (`.cloudcode`)** | Build + push all microservices |
| **Cloud Run Deployments** | Stateless FastAPI + strategy worker + AI analyst |
| **Cloud SQL** | PostgreSQL (private IP + VPC connector) |
| **Secret Manager** | Store Gemini API keys securely |
| **Monitoring** | Cloud Monitoring + OpenTelemetry tracing |
| **Backup** | Daily pgdump to GCS |

---

## 5. Testing Matrix
| Level | Description |
|--------|-------------|
| Unit | Risk calc, indicators, and vector logic |
| Contract | API responses conform to `04_api_spec.yaml` |
| Integration | Ingestion → backtest → persistence |
| Regression | Fixed seed backtest comparison |
| E2E | Full simulation from frontend to execution |

---

## 6. Acceptance Criteria Template
**Task:** Implement `can_execute` guardrail  
Given `risk_usd=10`, `sl_distance_usd=50`, `min_lot=0.01`  
When called, returns `{can_execute:true, lot:0.2, reason:"ok"}`  
Test: assert float tolerance in result.

**Task:** Implement `resample_1h_from_15m`  
Given 4 sequential 15m candles ending at hour close,  
Then 1H candle close matches last 15m close; timestamp = hour close.

---

## 7. Deliverables
- Execution module (Python) with FastAPI routes + unit tests.
- Vectorbt backtest notebook wired to `strategy-core`.
- API router implementations from `04_api_spec.yaml`.
- Next.js 15 dashboard scaffold.

---

## 8. Immediate Next Action
Generate the **Execution / Risk module** including:
- `execution/app/executor.py` (guardrails logic)
- `api-gateway/app/routers/risk.py` (FastAPI route)
- `tests/test_execution.py` (unit & contract tests)
- Dockerfile and Compose integration.

Once confirmed, development continues via Cloud Code with SDD validation checkpoints at each stage.

