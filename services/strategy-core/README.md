# MTF Olympus: Strategy Core Service

The **Strategy Core** is the high-performance analytical engine and execution hub of the MTF Olympus trading system. It is responsible for real-time market analysis, strategy orchestration, backtesting, and institutional-grade indicator calculations.

## 🚀 Overview

Strategy Core transforms raw market data into actionable trading signals using a decoupled, event-driven architecture. It supports both predefined "Institutional Templates" and dynamic, user-coded bots, all while maintaining a low-latency execution pipeline.

### Key Capabilities:
- **Real-Time Execution**: Processes live tick and candle data via Redis streams.
- **Vectorized Backtesting**: High-speed historical simulations leveraging [VectorBT](https://vectorbt.dev/).
- **Institutional Indicators**: Numba-accelerated implementations of Market Profile (TPO), SMC, and Multi-Timeframe Pivots.
- **Extensible Plugin System**: A hook-based architecture (Actions & Filters) for risk filters, sentiment guards, and notifications.
- **MTF Awareness**: Native support for Multi-Timeframe analysis (M1 to Monthly).

## 🏗️ Architecture

The service is built with **FastAPI** and utilizes a multi-layered design:

- **API Layer (`main.py`)**: Exposes analytical tools and lifecycle management endpoints.
- **Strategy Engine (`app/engine/`)**: The core orchestrator managing state, events, and signal generation.
- **Fleet Manager (`app/fleet.py`)**: Scales strategy deployments across multiple symbols and accounts.
- **Registry (`app/registry.py`)**: Dynamically discovers and loads specialized strategy modules.
- **Plugin Engine (`app/plugins/`)**: Decouples cross-cutting concerns (Risk, AI Sentiment) from core strategy logic.

### Data Flow
```mermaid
graph LR
    Redis[(Redis Streams)] --> LiveRunner[Live Runner]
    LiveRunner --> Engine[Strategy Engine]
    Engine --> Registry[Strategy Registry]
    Registry --> Strategies[Trading Strategies]
    Strategies --> Signal[Signal]
    Signal --> Plugins[Plugin Filters]
    Plugins --> Execution{{Execution Service}}
```

## 🛠️ Components

### 1. Market Profile & SMC
The `app/indicators` directory contains top-tier analytical tools:
- **TPO Profile**: Optimized with Numba for sub-20ms performance on large datasets.
- **SMC Engine**: Vectorized detection of Order Blocks, Fair Value Gaps (FVG), and Liquidity Sweeps.
- **MTF Pivots**: Support for Camarilla, Woodie, and Traditional levels across all timeframes.

### 2. Strategy Fleet
The **Fleet Manager** handles the lifecycle of:
- **Template Strategies**: Hardcoded institutional logics used for consistency.
- **Dynamic Bots**: User-provided Python code executed in a sandboxed environment (`DynamicBotExecutor`).

### 3. Plugin System
Leverages a WordPress-inspired `HookManager` to allow modular extensions:
- `on_market_data`: Enrich or filter incoming data.
- `filter_signal`: Apply global risk or sentiment constraints.
- `on_signal`: Trigger external notifications (Telegram, Webhooks).

## 🚦 API Reference (Highlights)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/calculate/smc` | `POST` | Get SMC analysis for a given dataset. |
| `/api/v1/calculate/market-profile` | `POST` | Generate TPO profile & POC/VAH/VAL. |
| `/api/v1/backtest` | `POST` | Run a vectorized historical backtest. |
| `/api/v1/strategies/{id}/start` | `POST` | Activate a live strategy instance. |
| `/api/v1/analysis/drift` | `GET` | Calculate system rejection and slippage rates. |

## 📦 Installation & Development

This service uses `uv` for lightning-fast dependency management.

### Prerequisites:
- Python 3.12+
- Redis (running on `localhost:6379`)
- PostgreSQL

### Local Setup:
```bash
# Install dependencies
uv sync

# Run the service with hot-reload
uv run uvicorn app.main:app --reload --port 8001
```

### Testing:
```bash
# Run unit and contract tests
uv run pytest
```

---
**MTF Olympus** | *Institutional Alpha at Scale*
