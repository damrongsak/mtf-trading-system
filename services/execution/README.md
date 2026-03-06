# MTF Olympus: Execution Service

The **Execution Service** is the institutional mandate-processor of the MTF Olympus platform. It handles the critical bridge between internal analytical signals and live broker execution, specifically optimized for **cTrader** via high-throughput WebSocket communication.

## 🏗️ Async RPC Architecture

The service operates as an autonomous background consumer, decoupling strategy logic from execution latency via a prioritized Redis-based "Buffer & Fire" model.

```mermaid
graph TD
    subgraph StrategyLayer["Strategy Engine"]
        SC[Strategy Core]
    end

    subgraph Messaging["Messaging Backbone"]
        PRIO[(queue:execution:priority)]
        CMD[(queue:execution:commands)]
        DLQ[(queue:exec:dead)]
    end

    subgraph Service["Execution Service"]
        WORKER[Prioritized Worker]
        IDEM[Idempotency Checker]
        ORDS[Order Service / Risk Check]
        ADAPT[cTrader Adapter]
    end

    subgraph Broker["Market Connectivity"]
        CT{{cTrader Account / LP}}
    end

    %% Flow
    SC -->|LPUSH| PRIO & CMD
    PRIO & CMD -->|BRPOP / Priority Shuffle| WORKER
    WORKER -->|Verify ID| IDEM
    IDEM -->|Process| ORDS
    ORDS -->|Sign & Send| ADAPT
    ADAPT -->|WebSocket| CT
```

## 🎯 Core Responsibilities

- **HFT-lite Execution Core**: Non-blocking, parallel risk validation with <100ms latency targets.
- **Tiered Caching**: Multi-level cache (In-memory + Redis) for accounts, funds, and decrypted credentials.
- **Sub-millisecond Price Resolution**: Direct-to-Redis price lookups with stale price protection.
- **Observability Tracing**: Millisecond-level execution tracing for performance auditing and bug detection.
- **Risk Citadel**: 6+ layers of automated risk filters (News, Volatility, Liquidity, etc.).
- **Async Command Processing**: Distributed consumption of trade signals with professional priority weighting (**Priority** > **Standard**).
- **Institutional cTrader Adaption**: High-fidelity orders (Market, Limit, Stop) with integrated Stop-Loss and Take-Profit tagging.
- **Idempotency & Safety**: Multi-layer protection against race conditions using Redis `SETNX` locking to ensure a signal is never executed twice.
- **Dead Letter Handling**: Automated retry logic (3 attempts) with routing to `queue:exec:dead` for manual intervention on failed orders.
- **Hierarchical Risk Citadel (3-Phase)**: Modular validation engine enforcing:
    - **Phase 1 (Core)**: Mandatory SL/TP, distance, and RRR validation.
    - **Phase 2 (Market)**: Real-time News, Session, Volatility, Quant, and Liquidity filters synced via Redis for HFT speeds.
    - **Phase 3 (Account)**: Daily Drawdown, Max Trades, and Consecutive Loss limits.
- **Equity Guardian**: Real-time monitoring of account equity and margin availability to enforce hard system-wide circuit breakers.
- **Institutional Resilience**: Professional-grade **Circuit Breakers** for broker connections, request **Timeouts** (15-30s), and a **Global Kill Switch** for emergency halts.
- **HFT-Lite Latency Suite**:
    - **TCP_NODELAY**: Immediate packet transmission (disabled Nagle's).
    - **Comprehensive L3 Adapter Cache**: DB-hydrated in-memory symbol and contract mapping for sub-millisecond execution resolution.
    - **Connection Warm-up**: Proactive broker session initialization.
- **🛡️ Sprint F Safety Guards** (implemented):
    - **Pre-trade Risk Validation**: SL/TP direction check in `amend_order` — LONG SL must be below entry, SHORT SL above. Violations return HTTP 422.
    - **`RiskValidationError`**: Custom exception class distinct from `ValueError` (404) to enable correct HTTP status codes.
    - **15 unit tests** covering all validation paths.
- **✅ Phase 1 — OANDA Live Integration** (Implemented):
    - **[O1] Live Environment Support**: Dedicated `OandaOrderAdapter` with `v20` API integration.
    - **[O2] Bracket Orders**: Automated SL/TP attachment to both Market and Limit orders.
    - **[O3] Order Amendment**: Support for `OrderReplace` to dynamically move Entry, SL, and TP on pending orders.
    - **[O4] Resilient Sync**: Validated against OANDA state sync delays with human-like simulation testing.
- **✅ Phase 15 — cTrader ID Stabilization** (Implemented):
    - **Stable ID Mapping**: Prioritizes `positionId` over `orderId` for filled market orders, ensuring persistent trade records align with broker requirements for amendments.
    - **Duplicate Prevention**: Re-engineered event filtering to skip `ORDER_ACCEPTED` and only publish true fill data.
    - **Deal Tracking**: Implemented `broker_deal_id` for robust deduplication across service boundaries.
    - **Reconciliation Enhancement**: Updated Janitor sync to include Pending Orders, preventing accidental pruning of working limit/stop orders.

## 🤖 AI-Agent Operational Guide

To modify execution behavior or troubleshoot connectivity, follow this path:

1.  **Command Flow**: The main consumer loop is in `app/worker.py`.
2.  **Broker Adapters**: The cTrader logic resides in `app/adapters/ctrader.py` and `app/adapters/ctrader_client.py`.
3.  **Modular Filters**: Phase 2 market filters are in `app/filters/`.
4.  **Risk Management**: Account-level limits (Phase 3) are in `app/risk/risk_limits.py`.
5.  **Minimax Integration**: Portfolio risk parity and regret minimizing logic is in `app/services/minimax_service.py`.

## 🚦 Operational Guide

### Common Issues & Fixes

| Symptom | Probable Cause | Fix |
| :--- | :--- | :--- |
| **Orders Stuck in Queue** | Worker is down or Redis full | Check `docker ps`; verify `EXECUTION_MAX_QUEUE_SIZE` in Strategy Core. |
| **cTrader Connection Error** | OAuth token expiry or network | Check logs for "ProtoOAAuthenticateRes"; verify connectivity to `proxy.ctrader.com`. |
| **cTrader Cancel Reject (2132)**| Order status mismatch or expiry | Normal cTrader API behavior for stale orders; check if order already filled. |
| **Idempotency Reject** | Duplicate signal delivery | Normal behavior (Signal protection); investigate why Strategy Core is double-firing. |

### Diagnostic CLI
Check worker health and current queue depths:
```bash
docker compose exec execution python -c "from app.health import check_queues; print(check_queues())"
```

## 📂 Directory Structure

```text
app/
├── adapters/          # Broker protocols (cTrader WebSocket, Binance, OANDA)
├── filters/           # Modular Phase 2 market condition filters (Redis-context aware)
├── risk/              # Phase 3 Account-level risk agents (Drawdown, Limits)
├── services/          # Business logic (Order Management, Minimax Risk, Equity Guardian)
├── validators/        # Phase 1 Core order parameter validation
├── core/              # Global schemas & configuration managers
├── executor.py        # Final risk-parameter calculation & validation
├── worker.py          # Prioritized Redis queue consumer (The Heart)
└── main.py            # API entry point & background task orchestration
```

## 🛠️ Multi-Broker Support
While **cTrader** is the primary institutional target, the service maintains a pluggable `BrokerFactory` for:
- **Binance**: Crypto spot/futures execution.
- **Mock**: For isolated testing environments.

---
**MTF Olympus** | *Institutional Alpha at Scale*
