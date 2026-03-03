# 🚀 MTF Olympus: Data Pipeline Service

The **Data Pipeline** is the high-performance ingestion engine and "Market Awareness" layer of the MTF Olympus trading system. It handles real-time data ingestion, historical backfilling, and institutional sentiment analysis.

---

## 🏗️ Architecture Overview

The service operates as a **Stateful Producer** in a de-coupled microservices architecture:
1.  **Ingestion Layer**: Pluggable adapters (cTrader & OANDA) fetch real-time ticks and OHLC candles.
2.  **State Management (ECST)**:
    - **L1 (In-Memory)**: High-frequency candle buffers for rapid indicator calculation.
    - **L2 (Shared Cache)**: Redis Hash stores (e.g., `market_data:spot:XAUUSD`) for cross-service state sharing.
    - **L3 (Database)**: PostgreSQL handles historical candles, news articles, and COT reports.
3.  **Broadcasting**: Real-time market events are broadcasted via **Redis Pub/Sub** to downstream consumers (Strategy Core, AI Analyst, Dashboard). Includes **EFP** (Spot/Futures spread) and predictive **Feature** data.
4.  **Adaptive Throttling**: Implements a 10Hz (100ms) safety cap on price updates to prevent dashboard and network saturation during high volatility.

### 🗺️ Data Flow Architecture
The following diagram illustrates the lifecycle of data from institutional ingestion to storage and downstream consumption.

```mermaid
graph TD
    subgraph External["External Sources"]
        CT_Live[cTrader Ticks]
        CT_Hist[cTrader Candles]
        EXT_NEWS[NewsAPI / SerpApi]
        EXT_CAL[ForexFactory]
        EXT_COT[CFTC Reports]
    end

    subgraph DP["Data Pipeline Service"]
        Stream[Stream Manager]
        Jobs[Scheduler & Backfill]
        DB_Sync[ORM / DB Writer]
    end

    subgraph Store["Storage & Messaging"]
        L2[(L2: Redis Hash Cache)]
        PubSub{Redis Pub/Sub}
        L3[(L3: PostgreSQL DB)]
    end

    subgraph Consumers["Downstream Consumers"]
        SC[Strategy Core]
        AI[AI Analyst]
        AGW[API Gateway / Dashboard]
    end

    %% Ingestion to Service
    CT_Live -->|WebSocket| Stream
    CT_Hist & EXT_NEWS & EXT_CAL & EXT_COT -->|Polling/REST| Jobs
    
    %% Service to Storage
    Stream -->|Atomic Update| L2
    Stream -->|Broadcast| PubSub
    Jobs -->|Save History| DB_Sync
    DB_Sync --> L3

    %% Storage to Consumers
    L2 -.->|Snapshot/Warmup| SC & AI & AGW
    PubSub -->|Live Ticks| SC & AGW
    L3 -.->|Historical Query| AI & AGW

    %% Feedback Loop
    AI -->|Sentiment Scores| DB_Sync
```

### 📰 News & Sentiment Engine
The pipeline includes a robust news ingestion and sentiment analysis framework:
- **Resilient Sourcing**: Primary hits via **NewsAPI** (optimized query mapping) with an automated fallback to **Google Search (SerpApi)** if quotas are exceeded or NewsAPI returns empty results.
- **Institutional Filtering**: Articles are filtered by **VIP Domains** (Bloomberg, Reuters, WSJ, etc.) to ensure high-quality signal generation.
- **Deduplication**: Content is normalized and deduplicated using URL-based MD5 hashing before being committed to PostgreSQL.
- **Sentiment Loop**: Receives and stores processed sentiment scores (calculated by the AI Analyst) to build long-term institutional bias charts.

---

## 🛠️ Environment Configuration

The service is configured via environment variables (see `.env` at root).

| Variable | Requirement | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | **Required** | PostgreSQL connection string. |
| `REDIS_URL` | **Required** | Redis connection (e.g., `redis://redis:6379/0`). |
| `CTRADER_TOKEN` | Optional | OAuth2 token for institucional data ingestion. |
| `SERPAPI_API_KEY` | Optional | Key for Google Search news fallback. |
| `NEWS_API_KEY` | Optional | Key for NewsAPI.org (Market sentiment). |

---

## 📡 API Documentation (v1)

### 📊 Market Data
- `GET /api/v1/candles`: Retrieve historical OHLCV data.
- `GET /api/v1/symbols`: Get active symbols for a specific broker.
- `POST /api/v1/backfill`: Trigger a background historical data ingestion job.

### 📰 Institutional & News
- `GET /api/v1/news/calendar`: Retrieve upcoming high-impact economic events.
- `POST /api/v1/news/calendar/sync`: Force a manual sync from ForexFactory.
- `GET /api/v1/news/headlines`: Fetch real-time institutional news for a symbol.
- `GET /api/v1/news/sentiment/history`: Retrieve historical sentiment scores and bias.
- `GET /api/v1/ingest/cot/latest`: Get latest CFTC Commitment of Traders sentiment.

#### 📊 Open Interest & Options Sentiment
- `POST /api/v1/ingest/oi`: Upload "Open Interest Matrix" Excel files.
- `GET /api/v1/oi/snapshots`: List available OI snapshots.
- `GET /api/v1/oi/details`: Get granular OI records (Strikes, Call/Put OI, DTE, Underlying Futures Price/Symbol).
- `GET /api/v1/oi/analysis`: Get Put-Call Ratio (PCR) and distribution analytics.

### 🧪 System Operations
- `POST /api/v1/stream/refresh`: Force restart of real-time streaming connections.
- `POST /api/v1/ingest/manual`: Manually trigger a data ingestion cycle.

### 🛡️ Resilience & Throttling
- **Adaptive Throttling**: Ticker updates are capped at 100ms intervals per symbol to protect downstream WebSocket consumers.
- **Circuit Breaker (Wait)**: All internal broker requests use fixed timeouts (15s) with automated reset logic.

---

## 🤖 AI-Agent Guidance (Ops Guide)

### 🚨 Common Troubleshooting
1.  **500 Error on API**:
    - **Check Database**: Ensure migrations are current. The service runs a **Startup Dry-Run Check** (`scripts/startup_check.py`) to verify table existence.
    - **Missing Table**: If `cot_records` or `economic_events` is missing, run `alembic upgrade head`.
2.  **No Price Updates**:
    - Check if the broker (cTrader) is in **Market Closed** hours (Weekends).
    - Verify `CTRADER_TOKEN` expiry via the logs.
3.  **High Memory Usage**:
    - Check for large candle backfills running in the background.

### 🚀 Management Commands
Execute these from the project root using Docker:
```bash
# Run migrations manually
docker compose exec data-pipeline alembic upgrade head

# Perform a manual health/dry-run check
docker compose exec data-pipeline python scripts/startup_check.py

# Manually trigger a calendar sync
docker compose exec data-pipeline curl -X POST "http://localhost:8000/api/v1/news/calendar/sync"
```

---

## 📂 Directory Structure

```text
app/
├── adapters/          # Low-level protocol clients (Fix/Protobuf)
├── scheduler/         # Background jobs (COT, News, Backfills)
├── streaming/         # High-performance event broadcasting
├── controllers/       # Business logic for data orchestration
└── main.py            # API entry point & stream lifecycle
```

---
**MTF Olympus** | *Institutional Alpha at Scale*

## 📦 Key Components
-   `app/adapters/`: Low-level protocol clients (Fix/Protobuf for cTrader).
-   `app/scheduler/`: Background jobs for non-realtime data (COT, News).
-   `app/streaming/`: High-performance broadcast management.
-   `scripts/entrypoint.sh`: Orchestrates migrations and dry-runs on startup.
