# Implementation Status

**Last Updated:** 2026-01-04
**Current Phase:** Phase 16 - Backfill Architecture Refactor (Complete)

---

## 🟢 Completed / Stable

### **1. Execution & Risk Engine (`services/execution`)**
- **Status:** ✅ Complete
- **Features:**
    - `can_execute` guardrail logic implemented.
    - Risk checks: Max risk ($10), Min lot (0.01), SL distance validation.
    - **OANDA Integration:**
        - `OandaAccountAdapter`: Fetches real-time NAV, margin, and position counts.
        - `OandaOrderAdapter`: Places market orders with integrated Stop Loss and Take Profit.
        - API endpoints: `GET /account/summary`, `POST /orders`.
    - **Dependency Management:** Migrated to `uv` (replaced `pip`/`requirements.txt`).
    - Unit tests passing (`tests/test_execution.py`).
    - Docker container builds successfully with `uv`.
    - Health check endpoint active.
    - **CORS:** Enabled `CORSMiddleware` to allow all origins.

### **2. Infrastructure (Local)**
- **Status:** ✅ Functional
- **Features:**
    - `docker-compose.yml` orchestrates API, Execution, Frontend, and Nginx.
    - Shared network `orignx-network` configured.
    - Hot-reload enabled for development.
    - **Nginx Reverse Proxy:** Configured to expose all services via port 80 (`infra/nginx/default.conf`), including a dedicated `/signal/` route to the API Gateway.
    - **API Versioning:** All services exposed under `/api/v1/`.
    - **Automated Testing:** `tests/test_endpoints.sh` verifies service health and signal endpoints.
    - **Docker Compose Enhancements**: Added missing `DATA_PIPELINE_URL` and `STRATEGY_CORE_URL` environment variables to `api-gateway`. Added volume mounts for `api-gateway`, `data-pipeline`, and `execution` for better local development.

### **3. Multi-Tenancy & Authentication**
- **Status:** ✅ Complete
- **Features:**
    - JWT-based authentication implemented.
    - User registration and login endpoints (`/api/v1/auth/token`, `/api/v1/auth/register`).
    - Multi-user support with UUID-based User model.
    - Fund and UserFund models for multi-tenancy.
    - RBAC roles (Owner, Manager, Trader, Viewer).
    - Database migrations applied via Alembic.
    - Password hashing with `bcrypt`.

### **4. Trading Journal Module**
- **Status:** ✅ Complete
- **Features:**
    - **Backend:**
        - 4 database models: `JournalEntry`, `MentalState`, `TimelineEvent`, `RootCauseAnalysis`.
        - CRUD API endpoints (`POST /api/v1/journal`, `GET /api/v1/journal`, `GET /api/v1/journal/{id}`).
        - Full integration with User authentication.
        - Database migrations applied.
    - **Frontend:**
        - "Psychological MRI" 4-step wizard:
            - Step 1: Technical Context (Risk/Money Management)
            - Step 2: Game Level (A/B/C categorization)
            - Step 3: Mental Pattern (Timeline builder + Severity sliders)
            - Step 4: Root Cause Analysis (5-field structured diagnosis)
        - Glassmorphism UI with color-coded severity feedback.
        - Auto-save support and API integration.

### **5. Strategy Engine & Oanda Integration**
- **Status:** ✅ Scaffolded
- **Features:**
    - `OandaAdapter` for market data ingestion (`services/strategy-core/app/adapters/oanda.py`).
    - `StrategyEngine` for managing concurrent strategy execution.
    - Strategy and DataSource models implemented.

### **6. Transaction Management & Portfolio Tracking**
- **Status:** ✅ Complete (2025-12-04)
- **Features:**
    - **Backend:**
        - Transaction model (Deposit/Withdrawal) with fund linkage.
        - CRUD API endpoints: List, Create, Update, Delete transactions.
        - Balance calculation endpoint.
        - Excel import with duplicate detection.
        - Database migrations applied.
    - **Frontend:**
        - Complete transactions page (`/transactions`).
        - Balance card with real-time updates.
        - Transaction list with pagination.
        - Create/Edit/Delete transactions UI.
        - Excel file import dialog.
        - Export to CSV/PDF.
        - Filter by type and date range.
        - Balance history chart (recharts).
        - Navigation link in sidebar.
    - **Commits:**
        - `d2d4771` (2025-12-04): Backend implementation
        - `eaacc69` (2025-12-04): Frontend integration
        - `6ca22d4` (2025-12-04): Enhancement features

### **7. Settings & User Preferences**
- **Status:** ✅ Complete (2025-12-04)
- **Features:**
    - User preferences model with strategy configuration.
    - User preferences model with strategy configuration.
    - Portfolio (Fund) management consolidated with Broker Accounts.
    - Settings page UI refactored (Profile only).
    - Dedicated Trading Preferences page.
    - Unit tests with 100% endpoint coverage.
    - **Commits:**
        - `bdbec98` (2025-12-04): Backend preferences model
        - `e2e9c8d` (2025-12-04): API client layer
        - `9b8112d` (2025-12-04): Settings page UI
        - `e62f561` (2025-12-04): Unit tests

### **8. Dashboard & Analytics**
- **Status:** ✅ Complete (2025-12-04)
- **Features:**
    - Realtime dashboard updates.
    - Manual refresh capability.
    - cTrader history import.
    - Advanced dashboard metrics.
    - **Commits:**
        - `9d036e5` (2025-12-04): Dashboard implementation
        - `ba83189` (2025-12-04): Realtime updates

### **9. Journal Analytics Dashboard**
- **Status:** ✅ Complete (2025-12-08)
- **Features:**
    - Enhanced Journal List View with Tabs.
    - Analytics Cards (Win Rate, P&L, R-Multiple).
    - Equity Curve integration (Area Chart).
    - Pattern Analysis (Game Level Pie Chart, Top Mental Patterns).
    - Backend API Integration (`/journal/analytics/*`).
    - **Commits:**
        - `166ea4b` (2025-12-08): Frontend implementation

### **10. API Gateway (`services/api-gateway`)**
- **Status:** ✅ Complete (2025-12-08)
- **Features:**
    - `/api/v1/risk/check` route implemented and connected to Execution service.
    - `/api/v1/signal` routes implemented (`GET /latest/{symbol:path}`, `POST /check`). Handles symbols with slashes.
    - `/api/v1/backtest` routes implemented (`POST /run`, `GET /results`).
    - `/api/v1/auth` routes: Login, Register, User details.
    - `/api/v1/strategies` routes: List and Create strategies.
    - `/api/v1/journal` routes: Create, List, Get journal entries.
    - **Streaming:** WebSocket endpoint `/api/v1/stream/prices` refactored to consume from Redis.
    - **Market Data:** Dynamic Category and Symbol management endpoints (`/api/v1/market/categories`).
    - Auth middleware with JWT token validation.
    - **CORS:** Configured `CORSMiddleware` to explicitly allow all origins.
    - **Schema Sync:** `Candle` model updated to include `is_complete` column and Alembic migration applied.
    - **Enum Update:** `NEUTRAL` direction added to `SignalDirection` enum.

### **11. Data Pipeline (`services/data-pipeline`)**
- **Status:** ✅ Complete (Refactored 2026-01-04)
- **Features:**
    - Service structure created.
    - `Candle` model defined.
    - Dockerfile updated to `uv`.
    - **Streaming Engine:** `StreamManager`, `RedisPublisher`, and `OandaStreamer` implemented for real-time data.
    - **Configuration:** DB-driven `DataSource` model.
    - **Audit Log:** `DecisionLog` and `AuditLogger` implemented.
    - **Oanda Integration:** `OandaClient` adapter implemented.
    - **Automation:** `APScheduler` configured to fetch M15, H1, H4 candles every 15m.
    - `POST /ingest/manual` endpoint for on-demand fetch.
    - **Database Integration:** Alembic configured, initial migration applied. `is_complete` column now present.
    - **API:** `POST /upload` (supports large CSV uploads via Nginx proxy) and `GET /candles` implemented.
    - **Dependencies:** `python-multipart`, `alembic` added to `pyproject.toml`.
    - **Historical Data Upload:**
        - Endpoint: `POST /api/v1/data/upload` (via Nginx proxy to Data Pipeline).
        - Robust CSV validation (schema, types, range checks).
        - Support for MetaTrader/Dukascopy CSV formats.
        - Efficient bulk upsert logic (INSERT ON CONFLICT UPDATE) to handle duplicates.
        - `updated_at` column added to `Candle` model via migration.
        - Nginx configured for large file uploads (50MB limit, 300s timeout).

### **12. Strategy Core (`services/strategy-core`)**
- **Status:** ✅ Complete (2025-12-08)
- **Features:**
    - Service structure created with `vectorbt`.
    - **Indicators:** EMA, ATR, RSI, MACD, Bollinger Bands endpoints.
    - **SMC:** Order Block (Displacement/Volume), FVG, and Liquidity Sweep detection.
    - **Simulation:** GRID regime simulation logic.
    - Unit tests verified via Docker.
    - **CORS:** Enabled `CORSMiddleware` to allow all origins.

### **13. AI Analyst (`services/ai-analyst`)**
- **Status:** ✅ Complete (2025-12-15)
- **Features:**
    - **Service:** `GeminiClient` (migrated to `google-genai` SDK) and `RAGService` implemented.
    - **API:** `/analyze/market` and `/analyze/journal` endpoints.
    - **Agent:** "Market Observer" Agent implemented using LangGraph and Tools.
    - **RAG:** User-aware memory with Qdrant vector store.
    - **Gateway:** Proxy router `ai.py` linked.
    - **Frontend:** `AIAnalystCard` integrated into Dashboard with real-time markdown reports.
    - **CORS:** Configured `CORSMiddleware` to explicitly allow all origins.
    - **Model ID:** Updated Gemini model ID to `gemini-1.5-pro`.
    - **Dependency:** Upgraded to Python 3.12 and LangChain 0.3+.
    - **Unit Tests:** Verified Agent and RAG logic.

### **14. GRID Simulation Lab (`services/strategy-core`)**
- **Status:** ✅ Completed (2025-12-07)
- **Features:** 
    - **Frontend:** Regimes Selector, Strategy Controls, Results Visualization.
    - **Backend:** GBM Synthetic Data, Vectorbt Engine Integration.
    - **API:** `/api/v1/simulation` proxy endpoint.

### **15. Backtesting Engine (`services/strategy-core`)**
- **Status:** ✅ Completed (2025-12-16)
- **Features:** 
    - **Frontend:** 
        - Dedicated `/backtest` page.
        - Configuration Form: Symbol, Timeframe, Dates, Capital, Fees, Slippage, JSON Params.
        - Results Dashboard: Equity Curve (Recharts), KPI Cards, Trade Log.
        - **Debug Console:** Real-time log panel (`DebugConsole.tsx`) for execution feedback.
        - **Optimization:** Grid Search UI for parameter tuning.
    - **Backend:**
        - `run_historical_backtest` logic using `vectorbt`.
        - **Fee/Slippage Simulation:** Integrated precise cost modeling.
        - **Benchmark Comparison:** "Buy & Hold" return calculation.
        - **Optimization:** Grid Search (`optimization.py`) and Monte Carlo (`monte_carlo.py`) modules verified.
        - API Endpoints: `POST /backtest/run`, `/optimize`, `/monte-carlo` (proxied via API Gateway).

### **16. Trade History & Management**
- **Status:** ✅ Complete (2025-12-15)
- **Features:** 
    - **Backend:** 
        - `GET /api/v1/execution/trades` endpoint with pagination and filtering. 
        - Oanda sync integration for open positions.
    - **Frontend:** 
        - Dedicated `/trades` page.
        - `TradesTable` component with sorting/formatting.
        - Advanced filtering: Date range, Status, Symbol search.
        - Sidebar navigation link.
    - **Specs:** OpenAPI integration (`PaginatedResponse_TradeResponse`).

### **17. Autonomous Strategy Bot (`services/strategy-core`)**
- **Status:** ✅ Complete (2025-12-15)
- **Features:** 
    - **LiveRunner:** 24/7 background loop in `app/runner/live.py`.
    - **Event-Driven Engine:** Reacts to real-time OANDA ticks via `PriceStreamer` broadcasting.
    - **Core Logic (SMC):** Implemented Macro Bias (H4), Setup Zone (H1), and Trigger (M15) rules in `app/logic.py`.
    - **Execution Guardrail:** Enabled trade placement in `StrategyEngine` with strict `LIVE_TRADING_ENABLED` flag safety check.
    - **MTF Resampling:** Dynamically resamples tick data to higher timeframes.
    - **Control API:** `POST /strategies/{id}/start` and `/stop` endpoints.

### **18. User Profile Management**
- **Status:** ✅ Complete (2025-12-17)
- **Features:**
    - **Backend:** `POST /api/v1/auth/profile/avatar` endpoint, `avatar_url` database field, static file serving.
    - **Frontend:** Avatar upload UI in Settings, Profile Dropdown integration.
    - **Infrastructure:** Nginx and Next.js proxy configuration for static files.
    - **Commits:**
        - `feat: implement user profile picture upload and display` (2025-12-17)

### 19. Multi-Broker Architecture
- **Status:** ✅ Complete (2025-12-22)
- **Features:**
    - **Backend:**
        - `BrokerAccount` model with AES-256 encrypted credentials (`app/utils/crypto.py`).
        - `BrokerFactory` pattern in Execution Service for dynamic adapter instantiation.
        - Stateless Execution Service API (`POST /orders` accepts config).
        - Multi-Account Sync logic in `TradeService`.
        - CRUD API: `/api/v1/accounts` endpoints.
    - **Frontend:**
        - **Broker Settings:** "Broker Accounts" management UI (List, Add, Delete) with confirmation modal.
        - **Market Watch:** Dynamic filtering based on user preferences.
        - **UI Components:** New `ConfirmationModal` and `Label` components.
    - **Testing:** `test_multi_broker.sh` integration test and `test_crypto.py` unit test passed.

### 20. Market Analysis & Dynamic Charts
- **Status:** ✅ Complete (2025-12-22)
- **Features:**
    - **Stacked Chart Layout:** Syncs Price, RSI, MACD, etc. in separate panels.
    - **Dynamic Timeframes:** Support for custom frames (4h, 1d) via URL params.
    - **Indicators:** EMA, ATR, RSI, MACD, ADX fully integrated.
    - **Architecture:** `ChartContainer` + React Context for cross-chart sync.
    - **Data Pipeline:** Event-driven updates via Redis for real-time candles.

### 21. Multi-User Strategy Configuration
- **Status:** ✅ Complete (2025-12-23)
- **Features:** 
    - **Strategy Templates:** `StrategyRegistry` implementation allowing reusable logic (e.g., SMC, MACD).
    - **Configuration UI:** JSON-based Wizard (`/strategies/configure`) for setting parameters per-instance.
    - **Risk Profiles:** User-defined risk settings (Risk per trade, Max Drawdown) per strategy.
    - **Dashboard Integration:** Global strategy selector for filtering P&L and Equity Curves.
    - **Optimized Backend:** `SharedMarketDataManager` to reduce API calls and `RedisConfigCache` for low-latency lookups.
    - **Execution:** Secure credential lookup in `ExecutionService` for multi-user trade routing.

### 22. Dashboard Signal Optimization
- **Status:** ✅ Complete (2025-12-23)
- **Features:**
    - **Recent Signals Card:** Redesigned UI with "Click to Trade", localized formatting, and 5-minute auto-refresh.
    - **Batch Processing:** Implemented `/api/v1/signal/batch` to fetch analysis for all watchlist symbols in a single request.
    - **Trade Modal:** Integrated order confirmation flow directly from the dashboard card.
    - **Optimization:** Filtered low-quality (NEUTRAL) signals to reduce noise.
    - **Performance:** Reduced card height and optimized polling to 5 minutes for resource efficiency.

### 23. Dynamic Strategy Sandbox
- **Status:** ✅ Complete (2025-12-25)
- **Features:**
    - **Live Editor:** In-browser Python code editor (Monaco) at `/strategies/editor`.
    - **Execution Engine:** Secure, isolated backtesting environment using `multiprocessing`.
    - **Security:**
        - Non-root Docker user (`trader`).
        - AST-based code sanitization (blocks `os`, `sys`, `subprocess`).
        - Cascading Timeouts (Frontend 310s, Gateway 305s, Core 300s).
    - **UI/UX:**
        - Collapsible configuration sidebar.
        - Standardized Symbol/Timeframe selectors.
        - Enhanced Console Log with Request/Debug info.
        - Date Picker with auto-ISO conversion.
    - **Data:**
        - Normalized timeframe handling ('15m' -> 'M15').
        - On-demand data/logs visibility.
        - `$0.00` metrics display fixed (Direct Accessors).
    - **API:**
        - `POST /backtest/custom` endpoint implemented and spec-compliant.

### 24. Deployment Manager (Live Execution)
- **Status:** ✅ Complete (2025-12-26)
- **Features:**
    - **Backend:** `deployments` table, `SavedStrategy` table, and API endpoints (`GET/POST /deployments`).
    - **Strategy Core:** `DynamicBotExecutor` for safe execution of custom strategies.
    - **Fleet Manager:** Refactored to handle mixed fleet (Static + Dynamic).
    - **Frontend:**
        - **Deploy Button**: Integrated into Strategy Editor.
        - **Deployment Dashboard**: List active/stopped bots, monitoring status.
        - **Config Modal**: Configure live/paper mode, symbol, timeframe.

### 25. Portfolio Consolidation
- **Status:** ✅ Complete (2025-12-30)
- **Features:**
    - **Frontend:**
        - **Funds & Accounts (`/portfolio`):** Unified view for Fund selection, Risk Params, and Broker Accounts.
        - **Trading Preferences (`/trading`):** Dedicated page for Timeframes/Symbols.
        - **Context-Aware Accounts:** Broker accounts are now filtered by and created for the selected Fund.

---

## 🟡 In Progress / Partial

### **1. Frontend (`frontend`)**
- **Status:** ✅ Signals Connected, Core UI Implemented
- **Completed:**
    - Next.js 16 + React 19 setup.
    - Tailwind CSS v4 configured with "Gridbot AI" theme.
    - `SignalCard` component and `/signals` page implemented and connected to API.
    - **Layout:** Fixed Sidebar and Sticky Header implemented.
    - **Mobile:** Mobile optimized layout (Collapsible Sidebar, Responsive Tables).
    - **Authentication:** `AuthContext` and Login Page (`/login`).
    - **Trading Journal Wizard:** Full 4-step wizard at `/journal/new`.


    - **AI Analyst:** Real-time Market Observer integration (`AIAnalystCard`).
    - **Performance:** Optimized Turbopack config (`./` root) and activated middleware.
- **Next Steps:**
    - **Testing:** End-to-End frontend testing.

---

## 🔴 Not Started / Pending

### **2. End-to-End Testing Strategy**
- **Status:** ✅ Initialized (2025-12-19)
- **Features:**
    - Playwright framework configured (`frontend/e2e`).
    - Critical flows verified:
        - **Auth:** Login/Register (`auth.spec.ts`).
        - **Dashboard:** Element visibility and Market Watch (`dashboard.spec.ts`).
        - **Journal:** Wizard completion (`journal.spec.ts`).
    - **Note:** Trading flow skipped due to environment mocking complexity.

---



### **Phase 7: Advanced Quantitative Integration (Completed)**
- **Status:** ✅ Complete (2026-01-01)
- **Features:**
    - **Risk Citadel Upgrade:** Integrated `PyPortfolioOpt` for Risk Parity sizing (DYnamic Volatility-based allocation). Hard $10 risk cap removed.
    - **Strategy Foundry Upgrade:** Integrated `Quantreo` for advanced feature engineering (Parkinson Volatility, Entropy).
    - **AI Analyst Tools:** Added `calculate_efficient_frontier` and `analyze_market_regime` tools.
    - **Backtest Engine:** Exposed advanced quant libraries to Custom Strategy Editor.


### **Phase 8: Professional Standards & ML Readiness (Completed)**
- **Status:** ✅ Complete (2026-01-02)
- **Features:**
    - **Core Metrics Engine (`metrics.py`):** Centralized CFA-standard library.
    - **Benchmark Integration (`benchmark.py`):** Alpha/Beta calculation against XAU/USD, BTC, SPY.
    - **ML Optimization:** Vectorized calculations for high-frequency training loops.
    - **Bias Prevention:** Strict `iloc[-2]` logic enforcement in Strategy Core.
    - **Backtest Metrics Card:** Professional visual dashboard for Sharpe, Sortino, Alpha/Beta.

### Phase 9: Olympus Plugin Architecture (OPA)
- **Status:** ✅ Complete (2026-01-02)
- **Features:**
    - **Database Schema:** Added `plugins`, `user_plugins`, and `audit_logs` tables.
    - **Migration:** Alembic migration applied.
    - **Core Engine:** `services/strategy-core/app/plugins/plugin_engine.py` implemented.
    - **Hooks:** `on_market_data` and `filter_signal` hooks injected into `StrategyEngine`.
    - **API Endpoint:** `POST /api/v1/plugins/{id}/activate` implemented.

### Phase 10: AI Developer Audit & Refactor
- **Status:** ✅ Complete (2026-01-02)
- **Features:**
    - **Audit:** Verified code against `MTF - Olympus_ AI Developer Checklist (Plugin Audit).md`.
    - **Refactor:**
        - **Safety:** Added global `on_plugin_error` hook and `try-except` wrappers in `HookManager`.
        - **Standards:** Added strict type hinting and enhanced logging to `plugin_engine.py`.
        - **Isolation:** Added `requirements.txt` to `Olympus-LSTM-Predictor`.
        - **Logic:** Implemented "Reckless" (Optimistic) vs "Prudent" (Volatility Scaling) modes in reference plugin.
    - **Resolution:** Performed full database reset and re-migration to fix schema inconsistencies.

### Phase 11: Application Maturity (UI & Data)
- **Status:** ✅ Complete (2026-01-03)
- **Features:**
    - **Backend:** `risk_guardrail` plugin implemented and seeded.
    - **Data:** `seed_benchmark.py` implemented for Alpha/Beta calculations.
    - **Frontend:** `PluginManagement` component created and integrated.
    - **Verification:** Verified backtest metrics and plugin toggle functionality.

### Phase 12: Settings Page Unification
- **Status:** ✅ Complete (2026-01-03)
- **Features:**
    - **UI:** Tabbed Settings interface (`Profile`, `Trading`, `Brokerage`, `Plugins`).
    - **Refactor:** Consolidated `BrokerAccountsSection`, `TradingPreferencesSection`, and `PluginManagement` into `settings/page.tsx`.
    - **Code Quality:** Resolved lint errors and strict type checking issues.

### Phase 13: Olympus Enhancements (Visual & Quant)
- **Status:** ✅ Complete (2026-01-03)
- **Features:**
    - **Automated Reporting:** Daily Briefing Agent (`ai-analyst`) and UI Card.
    - **Sentiment Analysis:** NewsAPI integration, Sentiment Scoring, and Strategy filtering logic.
    - **Volatility Filter:** ATR-based filtering and Opportunity Logging (`opportunity_logs`).
    - **Visualization:** "Skipped Trades" table (`SkippedTradesTable`) for transparency.
    - **Specs:** Updated PRD, Data Model, and API Spec.


### Phase 14: Binance Broker Integration
- **Status:** ✅ Complete (2026-01-03)
- **Features:**
    - **Backend:** 
        - `BINANCE` broker support in `api-gateway` (`broker_account.py`).
        - HMAC SHA256 signature generation for secure API requests.
        - Symbol fetching and categorization (`Crypto`) for Binance instruments.
    - **Frontend:**
        - Updated `BrokerAccountsSection` to support `BINANCE`.
        - Conditional "Secret Key" input field for Binance credentials.
    - **Verification:**
        - Unit tests (`test_broker_binance.py`) passing.

### Phase 15: Data Source Management
- **Status:** ✅ Complete (2026-01-04)
- **Features:**
    - **Backend:** 
        - `DataSource` schema defined with Pydantic serialization.
        - CRUD Router (`routers/data_source.py`) implemented for managing providers.
    - **Frontend:**
        - "Data Sources" tab in Settings page.
        - `DataSourcesSection` UI for List, Create, Update/Disable of global providers.
        - JSON Editor support for configuration.
        - API Client (`lib/api/data-sources.ts`) with properly typed response handling.

### Phase 16: Backfill Architecture Refactor
- **Status:** ✅ Complete (2026-01-04)
- **Features:**
    - **Backend:**
        - Moved backfill logic from `api-gateway` to `data-pipeline` service (Layer separation).
        - Created `POST /api/v1/backfill` endpoint in `data-pipeline`.
        - Refactored `api-gateway` to proxy backfill requests to pipeline via `httpx`.
        - Cleaned up obsolete `oanda_backfill` code.
    - **Validation:**
        - Verified with `bulk_backfill.sh` (1,143 job trigger).
        - Confirmed service stability via logs.
### Phase 17: Data Pipeline Optimization & Symbol Management
- **Status:** ✅ Complete (2026-01-05)
- **Features:**
    - **Performance:**
        - Added `is_active` flag to `market_symbols` and optimized `StreamManager` to filter inactive symbols.
        - Reduced API calls to OANDA, significantly lowering CPU Usage.
    - **Backend:**
        - `PATCH /api/v1/data/symbols/{id}` endpoint for symbol toggling.
        - Rich metadata response for `GET /api/v1/data/symbols`.
    - **Frontend:**
        - `SymbolManagementModal` with search and toggle functionality.
        - Integrated into Settings > Data Sources.

### Phase 18: Open Interest Data Pipeline
- **Status:** ✅ Complete (2026-01-05)
- **Features:**
    - **Backend (Data Pipeline):**
        - Refactored `OpenInterest` parsing logic to `data-pipeline` service.
        - `OpenInterestService` handles Excel parsing (Pandas/OpenPyXL).
        - `POST /api/v1/ingest/open-interest` endpoint.
        - Unit tests with `pytest`.
    - **Backend (API Gateway):**
        - Proxy endpoint `POST /api/v1/data/open-interest/upload`.
        - Database migration management.
    - **Frontend:**
        - `OpenInterestUpload` component with datetime picker.
        - `/data/open-interest` page.
    - **Database:**
        - `open_interest` table with historical snapshots logic.

### Phase 19: Clean Architecture & Refactoring (Data Pipeline)
- **Status:** ✅ Complete (2026-01-05)
- **Features:**
    - **Refactoring:**
        - Implemented **Service-Repository Pattern** in `data-pipeline`.
        - Decoupled `MarketRepository`, `CandleRepository`, `OpenInterestRepository`.
        - Removed raw SQL and direct DB access from Routes/Jobs.
        - Strict Type Hinting and Pydantic usage.
    - **Bug Fixes:** 
        - Fixed `MarketRepository` filter to strictly exclude inactive symbols from scheduler.
    - **Testing:**
        - >90% Unit Test Coverage (`tests/test_services`).
        - Automated Verification Script (`verify_all.py`).
    - **Performance:**
        - Optimization: Increased candle fetch batch size to 100 per request.

### Phase 20: Streaming Architecture Unification
- **Status:** ✅ Complete (2026-01-06)
- **Features:**
    - **Strategy Core:**
        - Unified `RedisSubscriber` implementation in `app/streaming/subscriber.py`.
        - Removed duplicate legacy streaming code (`utils/redis_subscriber.py`).
        - Enhanced `LiveRunner` to use robust pattern subscription (`psubscribe`).
        - Verified `LiveRunner` integration with `app/main.py` startup checks.
    - **API Gateway:**
        - Confirmed robust `StreamManager` implementation with multiplexing.
    - **Testing:**
        - Added dedicated streaming unit tests (`test_streaming.py`).
        - Achieved >80% test coverage for streaming components.

