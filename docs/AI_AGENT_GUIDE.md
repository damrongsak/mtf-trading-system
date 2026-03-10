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
            "units": units, # Positive for BUY, Negative for SELL
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
- **Order Fills**: `execution.filled.stream`

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

## 📋 Step 7: Standardized Handoff & Progress Tracking
To ensure continuity across multiple AI agent sessions or human developer handoffs, every major task must conclude with a standardized handoff report.

### 🏠 Storage Location
Store handoff files in the root `task/` directory.

### 🏷️ Naming Convention
Use the ISO date followed by the specific feature and status:
`YYYY-MM-DD-FEATURE-NAME-STATUS.md`
*(Example: `2026-03-08-AI-ANALYST-V2.2-POST-MORTEM-SENTINEL.md`)*

### 📝 Content Structure
Each handoff MUST include:
1.  **Current Status**: Date and overall phase status.
2.  **What Has Been Accomplished**: Detailed bullet points of completed features and technical fixes.
3.  **Just Finished / Verification**: Results of unit/integration tests and manual verification.
4.  **Next Steps**: Actionable items for the next agent (e.g., monitor performance, tune prompts).
5.  **Key Files**: List of critical files modified or new components created.

---
**MTF Olympus** | *Institutional Alpha at Scale*
