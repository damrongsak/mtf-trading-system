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
