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
1.  **Phase 3.1:** Implement `GeminiClient` and basic prompt engineering (Done).
2.  **Phase 3.2:** Connect Qdrant and implement RAG for Journal entries.
3.  **Phase 3.3:** Build LangChain "Market Observer" agent for daily reports.
