# 03 - AI Agent Specification

**Version:** 1.0  
**Status:** DRAFT (Phase 3)

---

## 1. Overview
The **AI Analyst** is a specialized microservice designed to act as a "Co-Pilot" for the trading system. Unlike the Strategy Core, which relies on rigid math and logic, the AI Analyst uses **Large Language Models (LLMs)** and **Retrieval Augmented Generation (RAG)** to provide semantic understanding of market conditions, news, and trading journaling.

## 2. Core Capabilities

### 2.1. Semantic Market Analysis
- **Goal:** Provide a "Narrative Bias" (Bullish/Bearish/Neutral) to augment technical signals.
- **Input:**
    - Recent OHLCV data (H4/D1 trends).
    - Economic Calendar events (e.g., CPI, FOMC).
    - Recent news headlines (from external APIs).
- **Process:**
    - LLM summarizes market context.
    - Generates a "Sentiment Score" (-1.0 to +1.0).
    - Outputs a key narrative (e.g., "Gold is rallying due to safe-haven demand").

### 2.2. Intelligent Journaling (Psychological MRI)
- **Goal:** Analyze trader behavior and identify psychological leaks.
- **Input:**
    - Trade logs (Entry/Exit, PnL).
    - User written journal entries (Mental State, Root Cause).
- **Process:**
    - **Pattern Recognition:** Uses RAG to compare current entry with historical "Tilt" or "Revenge Trading" patterns stored in Qdrant.
    - **Feedback Loop:** Suggests corrective actions (e.g., "Stop trading for 2 hours").

### 2.3. Multimodal Chart Analysis (New)
- **Goal:** Visual analysis of price action patterns (Head & Shoulders, Wedges) that are hard to describe mathematically.
- **Input:** Chart screenshots (images) from the frontend.
- **Process:**
    - Gemini Vision Model analyzes the image.
    - Correlates visual patterns with mathematical indicators.

### 2.4. Agentic Code Execution (New)
- **Goal:** Verify strategies by running them, not just hallucinating code.
- **Process:**
    - Agent generates Python code (using `vectorbt`).
    - Code is executed in a secure sandbox.
    - Results (PnL, Sharpe) are fed back to the agent to refine the strategy.

### 2.5. Real-Time Search Grounding (New)
- **Goal:** Incorporate live breaking news (not just scheduled calendar events).
- **Process:** Use Google Search Tool to find reasons for sudden volatility (e.g., "Why is Gold dropping?").

## 3. Architecture components

### 3.1. RAG Engine (Retrieval Augmented Generation)
- **Vector Database:** Qdrant
- **embedding Model:** `text-embedding-gecko` (Google) or `all-MiniLM-L6-v2` (Local).
- **Collections:**
    - `market_context`: Historical daily summaries.
    - `journal_entries`: Past trade reviews and psychological states.

### 3.2. Reasoning Engine (LangChain)
- **Orchestrator:** LangChain `AgentExecutor`.
- **Tools:**
    - `get_market_price(symbol)`
    - `get_account_exposure()`
    - `search_historical_patterns(query)`
    - `google_search(query)` (New)
    - `run_python_code(code)` (New)
- **Loop (OODA):**
    1.  **Observe:** Fetch data.
    2.  **Orient:** Retrieve similar historical contexts.
    3.  **Decide:** Formulate an opinion.
    4.  **Act:** Output analysis or alert.

## 4. Data Models

### 4.1. MarketNarrative
```python
class MarketNarrative(BaseModel):
    timestamp: datetime
    sentiment_score: float # -1 to 1
    summary: str
    key_drivers: List[str] # ["Inflation", "War", "Yields"]
    recommendation: str # "Risk Off", "Look for Longs"
```

### 4.2. PsychologicalProfile
```python
class PsychProfile(BaseModel):
    user_id: str
    current_state: str # "Tilted", "Focused", "Anxious"
    risk_flag: bool
    suggested_action: str
```

## 5. API Interface

### 5.1. Generate Analysis
- **POST** `/analyze/market`
- **Body:** `{ "symbol": "XAUUSD", "timeframe": "4H" }`
- **Response:** `MarketNarrative` object.

### 5.2. Journal Feedback
- **POST** `/analyze/journal`
- **Body:** `{ "entry_id": "...", "content": "..." }`
- **Response:** Analysis of the journal entry + RAG matches.

## 6. Integration Roadmap
Building an **AI-powered system** using a modern GenAI stack (LangChain, Gemini, Qdrant, PostgreSQL).

Given your background as a **full-stack AI engineer who thrives on designing and experimenting**, this roadmap plays directly to your strengths by focusing on core architectural components (memory, vector DB) and high-value agent development (RAG, Market Observer).

I can provide a technical breakdown and visualization of the architecture. 

### Integration Roadmap Breakdown

Here is a technical outline of the phases and how the components interact:

#### Phase 3.1: Implement GeminiClient and Basic Prompt Engineering (Done)

* **Goal:** Establish the foundational LLM connectivity and initial interaction logic.
* **Technical Implication:**
    * **GeminiClient:** This is the core communication layer with the Google Gemini API.
    * **Basic Prompt Engineering:** Developing system prompts and user templates to ensure the LLM (Gemini) provides relevant, structured responses. This is the **Brain** of your system.

#### Phase 3.2: Connect Qdrant and Implement RAG for Journal Entries

* **Goal:** Give the LLM access to proprietary, long-term memory (Journal Entries) via Retrieval-Augmented Generation (RAG).
* **Technical Implication:**
    * **Qdrant (Vector Store):** This will store the vector embeddings of your Journal entries.
        * **Ingestion Pipeline:** Journal entries must be chunked, embedded (using a Gemini embedding model), and indexed in a Qdrant collection.
    * **RAG Implementation:** When a query is made, a LangChain retriever will:
        1.  Convert the query into a vector embedding.
        2.  Perform a **similarity search** in Qdrant to find the most relevant journal entry chunks.
        3.  Pass those retrieved chunks (the "context") along with the original query to the GeminiClient for a context-aware response.
    * **Agent Memory (PostgreSQL):** PostgreSQL will likely serve as the **short-term memory/checkpointer** for the agents in Phase 3.3, tracking conversation history or agent state across turns using LangChain's `PostgresSaver` or similar checkpointer functionality.

#### Phase 3.3: Build LangChain “Market Observer” Agent for Daily Reports

* **Goal:** Create a complex, autonomous agent that uses the connected data sources to perform a specialized, high-value task.
* **Technical Implication:**
    * **Agent:** This will be built using the LangChain framework (likely with LangGraph for more complex orchestration).
    * **Tools:** The agent will be given **Tools** to perform actions:
        * **Journal RAG Tool:** A tool that queries the RAG system from Phase 3.2 (Qdrant) to pull historical context from Journal entries.
        * **External Data Tool:** (Implied) A tool to access real-time market data or external APIs to fulfill the "Market Observer" role.
    * **Daily Reports:** The agent's final action will be a reasoning step that synthesizes information from both the Journal RAG Tool and External Data Tool to generate the daily report.
    * **Long-Term Memory:** The agent's decision-making process (thoughts, observations, final reports) could also be selectively indexed back into Qdrant to form a richer, evolving long-term memory.
