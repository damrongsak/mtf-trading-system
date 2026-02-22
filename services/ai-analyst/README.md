# AI Analyst Service

## 🧠 Overview
The **AI Analyst Service** is a specialized microservice within the MTF Trading System. It leverages **Google Gemini 2.5 Pro** and **RAG (Retrieval-Augmented Generation)** to provide semantic market analysis and psychological insights for trading journals.

## 🏗️ Architecture & Dataflow

### System Overview
The service orchestrates AI agents and analysis tools using a modular architecture:
*   **FastAPI**: Entry point and router management (`main.py`).
*   **Agents**: Autonomous workers (`MarketObserver`, `StrategyAdvisor`, `DailyBriefing`).
*   **Services**: Core logic providers (`GeminiClient`, `RAGService`, `MemoryService`, `SentimentService`).
*   **Tools**: Specialized functions for market data, search, and system state.
*   **Persistence**: Redis (Short-term/Checkpoints) and Qdrant (Long-term/RAG).

### ⚡ High-Performance Features
The service is optimized for low-latency institutional analysis:
*   **Routing Precision**: Uses dynamic intent classification to minimize reasoning loops (resolved in 1-2 turns).
*   **Parallel Execution**: Tools are executed concurrently using `asyncio.gather`.
*   **Context & Token Pruning**:
    *   **Scratchpad Summarization**: Lengthy tool outputs (>= 6000 chars) are automatically summarized by Gemini Flash.
    *   **Dynamic RAG**: Adjustable `top_k` retrieval based on query complexity.
*   **Signal Buffering**: API Gateway level caching reduces redundant calculation load.

### Agent Workflows

#### Strategy Advisor (`StateGraph`)
The most complex flow, designed for interactive coaching and strategy design:
1.  **Query Optimizer**: `Gemini Flash` rewrites query and classifies INTENT (e.g., `RESEARCH`, `TOOL_USE`).
2.  **Router**: Splits logic based on intent (Research, Tool Use, etc.).
3.  **Retrieval (RAG)**: Fetches User Facts, System Docs, and Strategy Code from `Qdrant`.
4.  **Reasoning**: `Gemini Pro` generates a "Chain of Thought" plan.
5.  **Tool Selection**: `Gemini Flash` selects tools based on plan + tool registry.
6.  **Execution**: Runs selected tools (e.g., `GetAccountStatus`) in parallel.
7.  **Generation**: Synthesizes all context, tool outputs, and reasoning into a final response.
8.  **Memory**: Updates User Facts (Long-term) and Redis Checkpoint (Short-term).

#### Market Observer (`ReAct`)
A standard ReAct (Reason + Act) loop for autonomous market monitoring:
1.  **Input**: "Generate market report for XAUUSD".
2.  **LLM**: `Gemini Flash` decides which tool to call.
3.  **Tools**: `MarketStateTool`, `GetTechnicalSignalsTool`, `GoogleSearchTool`.
4.  **Loop**: Iteratively calls tools and feeds output back into LLM until analysis is complete.
5.  **Output**: Structured markdown report.

#### 🤖 Autonomous Monitoring Agents
Beyond interactive chat, the service runs background tasks to ensure system health:
1.  **Stability Observer**: Periodically checks predictor and data-pipeline health; alerts via Telegram on degradation.
2.  **Session Drift Monitor**: Analyzes the rejection/execution rate of live signals and generates drift reports.
3.  **Gold Sentiment Guardian**: Schedules real-time geopolitical and macro sentiment updates for XAUUSD.

## 🛠️ Tech Stack
*   **Python 3.11+**
*   **FastAPI**: High-performance web framework.
*   **Google GenAI SDK**: Official Python client for Gemini API (`google-genai`).
*   **Qdrant**: Vector database integration for RAG.
*   **uv**: Fast Python package installer and resolver.

## 🚀 Setup & Installation

### 1. Prerequisites
Ensure you have `uv` installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies
Navigate to the service directory and sync dependencies:
```bash
cd services/ai-analyst
uv sync
```

### 3. Environment Variables
Create a `.env` file in the service root or set the variables in your shell:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional (for RAG)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 🏃‍♂️ Running the Service

Start the development server with hot-reload:

```bash
uv run uvicorn app.main:app --reload --port 8002
```

The API will be available at:
*   **Docs:** [http://localhost:8002/docs](http://localhost:8002/docs)
*   **Health Check:** [http://localhost:8002/health](http://localhost:8002/health)

## 🧪 Testing

This service uses `pytest` for unit testing, with `pytest-asyncio` for async support.

To run the tests:

```bash
# Ensure PYTHONPATH is set to resolve 'app' module
uv run env PYTHONPATH=. pytest tests/
```

## 🖥️ CLI Chat
The service includes a professional CLI for interacting with the Agentic RAG system.

### Running with Docker (Recommended)
You can run the CLI directly inside the container. This ensures all dependencies (Rich, HTTPX) are present.

```bash
# 1. Update Lockfile (if needed) & Rebuild
docker compose run --rm ai-analyst uv lock
docker compose build ai-analyst

# 2. Run the CLI script (Connects to the running ai-analyst service)
docker compose run --rm -e API_URL=http://ai-analyst:8000 ai-analyst python scripts/chat_cli.py
```

### Running Locally
```bash
uv sync
uv run python scripts/chat_cli.py
```

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Check service health and connection to AI/RAG providers. |
| `POST` | `/analyze/market` | Generates a narrative market outlook. |
| `POST` | `/analyze/journal` | Analyzes a trading journal entry. |
| `POST` | `/analyze/smc-narrative` | Generates a narrative from SMC data (OBs, FVGs). |
| `POST` | `/agent/observer/run` | Triggers the Market Observer Agent for deep research. |
| `POST` | `/agent/briefing` | Triggers the Daily Briefing Agent. |
| `POST` | `/ai/chat/sessions/message` | Helper endpoint for Strategy Advisor chat. |

## 🛠️ System Toolset (Capabilities)
The AI Analyst can interact with the following system domains:
*   **Institutional SMC**: `smc_technical_analysis` (Order Blocks, FVGs, Bias).
*   **Machine Learning**: `get_predictor_forecast`, `get_predictor_signal`.
*   **Market Sentiment**: `market_state` (PCR, Regimes), `cot_analyst`.
*   **Economics**: `get_economic_calendar`, `google_search` (Real-time news).
*   **System Controls**: `smart_order`, `strategy_manager`, `get_system_health`.
*   **Quantitative**: `python_sandbox` (Custom correlation/modeling).

## 💡 Best Practices: Effective Prompting

To get the most out of the **Strategy Advisor Agent**, use "High-Fidelity Prompts" that combine multiple data dimensions.

### 🔑 The 4-Pillar Prompt Structure
1.  **Context**: Specify the date, symbol, and relevant timeframes (e.g., "H4 and D1").
2.  **Multidimensional Objective**: Ask for different analytical perspectives simultaneously (SMC, ML, Macro).
3.  **Constraint/Reference**: Reference your current portfolio, specific POIs, or system health.
4.  **Delivery Channel**: Explicitly request notifications if you want the result on Telegram.

### 📝 Example: Weekly Preparation Briefing
Use this prompt on Sunday/Monday morning to prepare for the session:
> "Tomorrow is Monday 2026-02-23. Help me prepare for the gold trading week ahead. Please perform the following analysis: 1. Macro structural bias for XAUUSD on 4H/Daily. 2. Key POIs (Order Blocks/FVGs) for the week. 3. ML price forecast for the next 5 steps from Olympus Predictor. 4. Market state and any significant news/sentiment drivers. Summarize these into a 'Weekly Preparation Briefing' and send it to my Telegram."

### 📝 Example: Deep Institutional Research
> "Perform a deep dive into Gold's institutional sentiment. Check the latest COT data, analyze the Open Interest drift between the Asia and London sessions, and correlate this with the current ML confidence score. Send a detailed technical report to my Telegram."

### 📝 Example: Strategy Development
> "I want to design a new strategy based on Volatility Mean Reversion. Can you look at our existing `smc_v1` strategy code, suggest how to add a GARCH-based filter, and provide the updated Python logic?"

## 📂 Project Structure

```
services/ai-analyst/
├── app/
│   ├── core/           # Configuration settings
│   ├── schemas/        # Pydantic models for Request/Response
│   ├── services/
│   │   ├── gemini.py   # Google GenAI Client wrapper
│   │   └── rag.py      # Vector store logic
│   └── main.py         # FastAPI entry point
├── tests/              # Unit tests
├── pyproject.toml      # Dependency and project config
└── README.md           # This file
```
