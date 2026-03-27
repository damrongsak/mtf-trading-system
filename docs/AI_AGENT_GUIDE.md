# AI Agent Integration Guide - MTF Olympus

This guide outlines the steps for an AI agent (e.g., Gemini, GPT, or custom LangGraph agents) to understand and interact with the MTF Olympus backend API.

## 🏗️ Step 1: Ingest Technical Specifications
The "Source of Truth" for all system capabilities is the `specs/` directory.

1.  **API Specification**: Read `specs/04_api_spec.yaml`. This file defines all available endpoints, request bodies, and response schemas.
2.  **Data Model**: Read `specs/03_data_model.yaml` to understand how trades, accounts, and signals are structured in the database.
3.  **Architectural Context**: Read `GEMINI.md` to understand the microservice layout and decoupled logic.

## 🔑 Step 2: Authentication & Security
Agents must authenticate with the **API Gateway** before calling downstream services.

- **Internal Service (Agent-to-Service)**: Use the `X-Internal-API-Key` header with the value defined in the environment variables.
- **User-Acting Agent**: Use standard JWT authentication (`Authorization: Bearer <token>`) to respect user permissions and risk limits.

## 🛠️ Step 3: Implement Tool Definitions
MTF Olympus follows a "Tool-First" design. Instead of making raw HTTP calls, wrap API endpoints into "Tools" that LLMs can understand.

### Mandatory Tool Standards (Resilience Layer)
All tools must adhere to the FOLLOWING standards to ensure system stability:
1. **Inherit from `BaseTool`**: Must use `app.core.base_tool.BaseTool`.
2. **Implement `run_tool`**: Logic must reside in `async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs)`.
3. **Use Scaffolding**: NEVER create a tool from scratch. Always use the scaffolding script:
   ```bash
   docker compose exec ai-analyst python scripts/scaffold_tool.py --name "YourToolName"
   ```
4. **Input Normalization**: Handle both Pydantic models and dictionary inputs.
5. **Timeout Guardrail**: The `BaseTool` automatically applies a 60s timeout. Ensure IO operations are optimized.

### Example Tool Implementation (Python/LangChain style)
```python
from app.core.base_tool import BaseTool
import aiohttp

class PlaceOrderTool(BaseTool):
    name: str = "place_execution_order"
    description: str = "Places a market order via the Execution service."

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        # 1. Normalize Input
        symbol = "XAUUSD"
        units = 1000
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            units = input_data.get("units", units)
        
        # 2. Prepare Payload
        payload = {
            "symbol": symbol,
            "units": abs(units), # v2.1 Standard: ALWAYS Absolute
            "side": "BUY" if units > 0 else "SELL", # v2.1 Standard: Explicit Side
            "order_type": "MARKET"
        }
        
        # 3. Call Gateway with metadata context
        async with aiohttp.ClientSession() as session:
            url = f"{GATEWAY_URL}/api/v1/orders"
            headers = {"Authorization": f"Bearer {auth_token}"}
            async with session.post(url, json=payload, headers=headers) as resp:
                result = await resp.json()
                return f"Execution Response: {result}"
```

## 🧠 Step 4: Reasoning & Orchestration
Use an orchestration framework like **LangGraph** to manage complex workflows.

- **Decomposition**: Break high-level user requests into tool calls.
- **Validation**: Allow the agent to check risk limits (`/account/summary`) before placing a trade.
- **Looping**: If a trade fails (e.g., cTrader Error 2132), the agent should parse the error and retry with adjusted parameters.

### 🆔 Broker ID Lifecycle (CRITICAL)
Agents must handle differing identifier lifecycles across brokers:
- **STRICT SYMBOL NAMING**: Always use underscores (`XAU_USD`) in the database. Slashes are for display only.
- **CTRADER METADATA**: Never create cTrader symbols without the mandatory `details` fields (lot_size, pipPosition, symbol_id). See `GEMINI.md` for the full list.
- **NO IMPLEMENTATION without SPEC**: You MUST NOT modify Python/React code until the corresponding `.yaml` or `.md` spec in `specs/` is updated.
- **OANDA**: `orderID` is stable for both pending and filled states.
- **cTrader**: 
    - `orderId` is used for **Pending/Accepted** state.
    - `positionId` is the **Stable ID** for **Filled/Open** trades.
    - **Rule**: When amending an open trade on cTrader, use the `positionId` (stored in `broker_trade_id`).
    - **Deduplication**: Use `broker_deal_id` (metadata) to ensure one data-sync event per trade fill.

## 📡 Step 5: High-Frequency Path (HFT-lite)
For sub-millisecond data needs or high-performance execution, agents should bypass standard REST polling.

### 1. Market Data (O(1) Resolution)
Instead of `/market/snapshot`, read the direct Redis Hash:
- **Keys**: `market_data:spot:{SYMBOL}`
- **Fields**: `bid`, `ask`, `timestamp`, `volume`

### 2. Execution Tracing
Monitor the `execution_trace:{trace_id}` Redis key to get millisecond-level feedback on order processing steps.

### 3. Redis Streams
Subscribe to these for event-driven logic:
- **Market Data**: `market.trade.stream`
- **System Events**: `system.log.stream`
### 3. Order Fills & Persistence (HFT-Lite)
Monitor the `execution.filled.stream` for real-time trade updates.
- **DECOUPLED PERSISTENCE**: The API Gateway MUST NOT create any `Trade` records. Persistence is handled exclusively by the Execution Service background worker to prevent zero-price placeholders.
- **LOT SCALING STANDARD**: Raw broker units must be scaled to standard lot sizes using a **100,000.0** divisor (e.g., 1000 units = 0.01 lots). This standard is universal.
- **HIERARCHICAL CONTEXT**: AI agents MUST resolve the `User -> Fund -> Account -> Symbol` hierarchy before execution. Refer to [Institutional Execution Standard](file:///home/dan/workspace/mtf-trading-system/docs/INSTITUTIONAL_EXECUTION_STANDARD.md) for formulas.
- **DETERMINISTIC UUIDs**: Always use `uuid.uuid5(uuid.NAMESPACE_DNS, f"{account_id}_{broker_order_id}")` for trade identification.
- **GOLDEN RULE (V2.1)**: NEVER send signed units to the API Gateway or Execution Service. ALWAYS use strictly positive (absolute) `units` and specify the `side` (`BUY` or `SELL`) explicitly. Rejection (400) occurs if `units <= 0`.

## 🏁 Summary Checklist
- [ ] Parse `04_api_spec.yaml`.
- [ ] Configure `X-Internal-API-Key`.
- [ ] Map API routes to Pydantic-validated Tools.
- [ ] Ingest `GEMINI.md` for role-playing and persona context.
- [ ] (Advanced) Sync with **Qdrant** for long-term memory and RAG.

## 🔐 Step 6: Configuration & Environment Management
To maintain a "Single Source of Truth" and prevent configuration drift:
- **Centralized Environment**: All core API keys (e.g., `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`) must be stored ONLY in the project root `.env` file.
- **Service-Level Cleanup**: DO NOT create local `.env` files within individual microservice directories.
- **Docker Integration**: All services are configured via `docker-compose.yml` to read the root `.env` file automatically.

## 📋 Step 7: Professional Strategy Lifecycle (Idea-to-Live)
Agents implementing or deploying strategies MUST follow the **7-Step Olympus Standard**:

1.  **Logic Spec (08_logic)**: Define rules in YAML/Markdown before any Python code.
2.  **Vectorized Backtest**: Use `vectorbt` for 1-Year historical validation with realistic slippage.
3.  **Monte Carlo**: Run 1,000 simulations. **Ruin Probability < 1%** is mandatory.
4.  **Walk-Forward (WFA)**: Validate out-of-sample stability. Robustness Score > 60%.
5.  **1:1:1 Mapping**: Configure JSON (Strategy -> Fund -> Dedicated Broker Account) for clean audits.
6.  **Shadow Trading**: (Requirement) Run on live data for 5+ days to measure execution drift.
7.  **Drift Monitoring**: Use `PerformanceMonitor` to detect "Alpha Decay" and signal skipped vs. taken.

---
## 🛡️ Step 8: Strategy Registration & Ticking (Institutional Guardrails)
To maintain system integrity and auditability, AI agents MUST follow these rules when working with strategies:

### 1. The "UUID Only" Rule
- **RESTRICTION**: The `/api/v1/strategies/{id}/tick` endpoint only supports database-backed UUIDs.
- **ERROR HANDLING (422)**: If you provide a non-UUID string (e.g., `sentinel_v1`), the API will return a **422 Unprocessable Entity**. This is a schema validation failure, NOT a 404.
- **ERROR HANDLING (403/404)**: If the UUID is valid but you lack permissions, you receive a **403 Forbidden**. If the UUID does not exist, a **404 Not Found**.

### 2. Signal Traceability & Reasons (V2.1 Standard)
- **MANDATORY**: Every tick response MUST include a human-readable `reason` field.
- **TEMPLATE RULE**: Return a dictionary containing `{"signal": ..., "reason": "..."}`.
- **DYNAMIC RULE**: The `strategy()` function MUST return a `reason` key in its signal dictionary or a 4-element tuple where the 4th element is a log string/dict.
- **OBSERVABILITY**: Use `GET /api/v1/strategies/{id}/logs` to fetch the last 100 internal calculation logs.

### 3. Strategy Professionalization (Sandbox & Imports)
- **STANDARD IMPORTS**: Always use `import datetime`, `import json`, and `import time`. Avoid `from datetime import datetime` to prevent module shadowing.
- **SANDBOX GLOBALS**: In the dynamic executor, `pd`, `np`, `vbt`, `datetime`, `json`, and `time` are injected into `local_scope`. You do not need to re-import them inside the strategy function, though doing so is harmless.
- **HYDRATION**: Newly instantiated strategies require a ~2s "warm-up" period for the FleetManager to sync state from DB.

### 4. Strategy Registration & On-Demand Instantiation
- **ON-DEMAND**: Institutional users should use `POST /api/v1/strategies/instantiate` to deploy new instances from templates.
- **MANUAL (Legacy)**: If using physical folders:
1.  **Append to Master Data**: Add the strategy metadata and a unique UUID to `master_data/strategies.json`.
2.  **Sync to DB**: Run the MDMS import:
    ```bash
    docker compose exec api-gateway python scripts/manage_master_data.py import
    ```
3.  **Fleet Reload**: Trigger a reload in Strategy Core:
    ```bash
    curl -X POST http://localhost:8000/api/v1/strategies/reload
    ```

### 3. Verification Script
Use the built-in audit script to verify fleet health:
```bash
docker compose exec strategy-core python verify_fleet_uuid.py
```

## 📋 Step 9: Standardized Handoff & Progress Tracking
To ensure continuity across multiple AI agent sessions, all significant architectural changes or logic fixes MUST be documented in a handoff artifact.

### 📝 Content Structure
Each handoff MUST include:
1.  **Current Status**: Date and overall phase status.
2.  **What Has Been Accomplished**: Detailed bullet points of completed features and technical fixes.
3.  **Just Finished / Verification**: Results of unit/integration tests and manual verification.
4.  **Next Steps**: Actionable items for the next agent (e.g., monitor performance, tune prompts).
5.  **Key Files**: List of critical files modified or new components created.

*(Example: `2026-03-08-AI-ANALYST-V2.2-POST-MORTEM-SENTINEL.md`)*

## 🔍 Step 10: Standardized Logging (Observability)
To comply with **Observability Guardrails**, all services must implement structured JSON logging.

### 1. JSON Configuration
Use `python-json-logger` in `app/logging_config.py`. Ensure a `TracingFilter` is used to inject the `request_id` or `correlation_id` from the singleton utility.

```python
# Standard Filter Pattern
from app.utils.tracing import request_id_ctx
class TracingFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get() or ""
        return True
```

### 2. Traceability in Services
- **FastAPI**: Apply `RequestIDMiddleware` to capture headers.
- **Workers**: Set the correlation context at the start of task processing.

```python
# Worker ID Handling
correlation_id = message.get("correlation_id") or str(uuid.uuid4())
token = correlation_id_ctx.set(correlation_id)
try:
    await process_task(...)
finally:
    correlation_id_ctx.reset(token)
```

Refer to `specs/13_logging_standard.md` for the full schema requirements.

## 🕸️ Step 11: Service Communication Patterns (Resilience)
To avoid deadlocks and high-coupling, follow these patterns when designing inter-service logic:

| Pattern | Usage | Benefit |
| :--- | :--- | :--- |
| **ECST** | Frequently read data (News, Metadata) | O(1) Local Reads, No Network I/O. |
| **CQRS Read Model** | Complex queries / RAG | Optimized schema, no source-of-truth stress. |
| **API Composition** | Gateway responses only | Gateway aggregates; Services stay decoupled. |
| **Async RPC** | High-latency/Risk actions | Non-blocking, built-in retries/queuing. |

**CRITICAL RULE**: **NEVER** call the `api-gateway` from an internal service tool. If Service A needs data from Service B, call B directly or use a cached Event-Carried state.

## 💾 Step 12: Initial Seeding & Environment Setup
For a fresh environment, AI agents should ensure the following sequence is executed in the `api-gateway` service:

1.  **System Config**: `seed_system.py` (Ensures M1+ timeframes).
2.  **Market Data**: `seed_market_data.py` (Filters to EURUSD, USDJPY, BTCUSD, XAUUSD, WTI).
3.  **Broker Auth**: `seed_ctrader.py` (Links `trader1` to cTrader).
4.  **Test Data**: `seed_test_data.py` (Enforces trader1 -> cTrader and trader2 -> OANDA mappings).
5.  **Demo Setup**: `setup_ctrader_demo.py` (Configures `demo1` and account `9919680`).

---
**MTF Olympus** | *Institutional Alpha at Scale*
