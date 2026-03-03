# MTF Olympus AI - Architecture Analysis & Improvement Plan

**Document Type:** Technical Assessment  
**Date:** 2026-03-03  
**Analyst:** Soda (Quantitative Engineer AI)  
**Scope:** `/home/dan/workspace/mtf-trading-system/services/ai-analyst`

---

## 1. Executive Summary

The MTF Olympus AI represents a **production-grade institutional agentic system** with sophisticated LangGraph-based orchestration, semantic caching, and comprehensive tool coverage. The architecture demonstrates strong engineering principles: clear separation of concerns, strict data fidelity enforcement, and thoughtful fallback mechanisms.

**Current Maturity:** ~70% of a full quant analyst capability

**Key Strengths:**
- Agentic RAG with iterative refinement (Evaluator node)
- Strict data fidelity enforcement (Tool Result Supremacy doctrine)
- Comprehensive tool ecosystem (SMC, OI, Market State, Predictor)
- Semantic caching with Redis
- Context pruning to prevent token saturation

**Critical Gaps:**
1. Absence of autonomous self-correction loops
2. No episodic memory for trade outcome learning
3. Manual (not automated) risk integration in workflow
4. Single-symbol focus, no portfolio-level reasoning
5. Limited backtesting integration in agent flow

---

## 2. Architecture Deep-Dive

### 2.1 Current Flow

```
User Query → Query Optimizer → Router → [Tool Selection / Reasoning / RAG] 
           → Execute Tools → Summarizer → Generate → Evaluator → Memory Write
```

### 2.2 Tool Ecosystem

| Category | Tools | Coverage |
|----------|-------|----------|
| **Technical** | SMC Analysis, Signals, Volatility Structure | Excellent |
| **Fundamental** | News, Calendar, Google Search | Good |
| **Institutional** | OI, COT, Market State, EFP | Excellent |
| **Risk** | Risk Check (Manual), Risk Map | Partial |
| **Execution** | Smart Order, Strategy Manager | Good |
| **ML** | Predictor Forecast/Signal | Good |
| **Knowledge** | Quant Library RAG | Good |

### 2.3 Model Configuration

- **Primary:** `gemini-2.5-pro`
- **Fast:** `gemini-2.5-flash`
- **Lite:** `gemini-2.5-flash-lite`
- **Embedding:** `gemini-embedding-001` (3072-dim)

---

## 3. Gap Analysis & Recommendations

### 3.1 Self-Correction Mechanism (HIGH PRIORITY)

**Current State:** The Evaluator node judges response quality but lacks **autonomous correction capability**. When unsatisfactory, it only loops back to decomposition — it doesn't actively call diagnostic tools to verify hypotheses.

**Proposed Enhancement:**

```python
# Add to AgentState
class AgentState(TypedDict):
    # ... existing fields
    correction_attempts: int
    hypothesis_verification: Dict[str, bool]  # Track which hypotheses were tested
    
# New Node: hypothesis_tester
async def node_hypothesis_tester(state: AgentState):
    """
    Actively verifies hypotheses before final response.
    """
    feedback = state.get("evaluation_feedback", "")
    
    # Map feedback to verification tools
    verification_map = {
        "price incorrect": "smc_technical_analysis",
        "news stale": "google_search", 
        "risk unclear": "risk_check",
        "volatility misestimated": "volatility_structure_analysis"
    }
    
    # ... implementation
```

**Rationale:** Institutional analysts don't just "rethink" — they actively verify assumptions with data. This mimics that behavior.

---

### 3.2 Episodic Memory System (HIGH PRIORITY)

**Current State:** Memory service stores **facts** (`add_user_fact`) but lacks **episodic memory** — the system doesn't learn from trade outcomes.

**Proposed Enhancement:**

```python
# New table: trade_outcomes
class TradeOutcome(TypedDict):
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    reasoning: str  # Why the trade was taken
    actual_outcome: str  # What actually happened
    lessons: str  # What we learned
```

**New Node:** `node_learn_from_outcomes`

```python
async def node_learn_from_outcomes(state: AgentState):
    """
    Query recent closed trades and extract patterns.
    """
    # 1. Fetch last 10 closed trades
    trades = await fetch_closed_trades(limit=10)
    
    # 2. Analyze patterns
    prompt = f"""
    Analyze these trades for systematic errors:
    {trades}
    
    Identify:
    1. Winning pattern (what works)
    2. Losing pattern (what fails)
    3. One actionable insight to improve
    """
    
    insight = await gemini.generate(prompt)
    
    # 3. Store as episodic memory
    await memory.store_episode("trade_patterns", insight)
    
    return {"learned_insight": insight}
```

**Rationale:** A quant fund without trade journaling is flying blind. The system should actively learn from its own performance.

---

### 3.3 Automated Risk Integration (MEDIUM PRIORITY)

**Current State:** Risk check is a **manual tool call** — the agent must explicitly call `risk_check`. It's not automatically enforced.

**Proposed Enhancement:**

```python
# In node_generate, add pre-flight check
async def node_generate(state: AgentState):
    # ... existing code
    
    # Auto-inject risk analysis if trade is proposed
    if "buy" in response.lower() or "sell" in response.lower():
        risk_analysis = await risk_tool.run({
            "symbol": extract_symbol(state),
            "direction": extract_direction(response),
            "entry_price": extract_price(response)
        })
        
        response += f"\n\n**Automated Risk Assessment:**\n{risk_analysis}"
    
    return {"final_response": response}
```

**Alternative:** Add a `risk_guardrails` node in the graph that intercepts before execution.

---

### 3.4 Portfolio-Level Reasoning (MEDIUM PRIORITY)

**Current State:** All tools analyze **single symbols**. There's no portfolio context.

**Proposed Enhancement:**

```python
# New Tool: portfolio_context
class PortfolioContextTool(BaseTool):
    name = "portfolio_context"
    description = "Get current portfolio exposure, correlation, and risk contribution"
    
    async def run(self, input_data, auth_token):
        # 1. Get all open positions
        positions = await api.get_positions()
        
        # 2. Calculate exposure
        total_exposure = sum(p['notional'] for p in positions)
        gold_exposure = sum(p['notional'] for p in positions if p['symbol'] == 'XAUUSD')
        
        # 3. Return portfolio context for the agent to consider
        return f"Current Gold Exposure: {gold_exposure/total_exposure*100}%"
```

**Rationale:** Institutional desks think in portfolio terms, not just "what's the setup on gold?"

---

### 3.5 Multi-Modal Chart Analysis (MEDIUM PRIORITY)

**Current State:** No image/chart analysis capability.

**Proposed Enhancement:**

```python
# Add to tools
class ChartAnalysisTool(BaseTool):
    name = "analyze_chart"
    description = "Analyze a chart image for patterns, support/resistance, and setup quality"
    
    async def run(self, image_b64: str, symbol: str, timeframe: str):
        # Use Gemini's native image understanding
        response = await gemini.generate([
            Prompt(text="Analyze this chart..."),
            image_b64
        ])
        return response
```

**Use Case:** User sends screenshot of their chart → Agent evaluates the setup quality.

---

### 3.6 Backtesting Integration (LOW PRIORITY)

**Current State:** `backtest_runner` tool exists but isn't integrated into the agent's reasoning flow.

**Proposed Enhancement:**

```python
# When agent proposes a strategy, automatically backtest it
async def node_strategy_proposer(state: AgentState):
    proposed_strategy = state.get("proposed_strategy")
    
    # Auto-backtest before presenting
    bt_result = await backtest_tool.run(proposed_strategy)
    
    return {
        "strategy": proposed_strategy,
        "backtest": bt_result,  # Inject into response
        "confidence": calculate_confidence(bt_result)
    }
```

---

### 3.7 Explicit Regime Detection (LOW PRIORITY)

**Current State:** Regime detection is implicit in `market_state` tool (PCR, Max Pain).

**Proposed Enhancement:**

```python
# Add to AgentState
regime: str  # "trending", "range", "volatile", "quiet"

# New Node: regime_detector
async def node_regime_detector(state: AgentState):
    data = await asyncio.gather(
        market_state.run(symbol),
        volatility.run(symbol)
    )
    
    # Simple rule-based regime
    if data['atr'] > threshold * 2:
        regime = "volatile"
    elif data['adx'] > 25:
        regime = "trending"
    else:
        regime = "range"
        
    return {"regime": regime}
```

---

## 4. Quant Library Integration Enhancement

### 4.1 Current State
- 46 quant books ingested
- Semantic search with hybrid scoring
- Gemini reranking

### 4.2 Recommended Enhancements

**4.2.1 Concept Graph**

Build a graph of quant concepts for better retrieval:

```python
# Example: When user asks about "Kelly Criterion"
# Current: Returns relevant chunks
# Proposed: Returns concept map + related formulas + implementations
```

**4.2.2 Formula Extraction**

Extract and normalize formulas for calculator integration:

```python
# Extract from library
FORMULAS = {
    "kelly_criterion": "f* = (bp - q) / b",
    "sharpe_ratio": "(Rp - Rf) / σp",
    "sortino_ratio": "(Rp - Rf) / σd",
}
```

**4.2.3 Strategy Template Library**

Pre-built strategy templates accessible via natural language:

```
User: "Give me a mean reversion strategy for gold"
→检索: "mean reversion template"
→填充: Strategy with Gold-specific parameters
```

---

## 5. Risk Parameters Alignment

### 5.1 Current System Parameters

From today's session:
| Parameter | Value |
|-----------|-------|
| SL_DISTANCE | 200 pips |
| RR_RATIO | 1.5 (minimum) |
| NEWS_FILTER | ±30 min |
| MAX_DAILY_DRAWDOWN | $30.00 |
| Lot | 0.01 |

### 5.2 System Integration Gaps

1. **SL Distance:** Not enforced in `risk_check` — only calculated post-hoc
2. **RR Ratio:** Not validated against minimum before order
3. **Daily Drawdown:** No automated kill-switch in workflow

**Recommended:** Add `risk_parameters` to `UserConfig` and enforce in workflow:

```python
class UserConfig(TypedDict):
    # ... existing
    risk_params: Dict[str, float]  # {sl_distance: 200, rr_min: 1.5, max_dd: 30}
```

---

## 6. Implementation Roadmap

### Phase 1: Quick Wins (1-2 weeks)
- [ ] Add hypothesis verification node
- [ ] Auto-inject risk analysis before trade proposals
- [ ] Add portfolio context tool

### Phase 2: Core Intelligence (2-4 weeks)
- [ ] Build episodic memory for trade outcomes
- [ ] Implement regime detection node
- [ ] Add chart analysis capability

### Phase 3: Advanced Features (4-8 weeks)
- [ ] Portfolio-level reasoning
- [ ] Strategy auto-backtesting
- [ ] Concept graph for quant library

---

## 7. Conclusion

The MTF Olympus AI is a **well-engineered institutional system** with strong fundamentals. The primary opportunity is transforming it from a **reactive tool** (responds to queries) into a **proactive analyst** (learns from outcomes, verifies hypotheses, manages risk autonomously).

The recommended enhancements align with Dan's request: "Make Olympus AI work like Soda while preserving its unique capabilities."

---

**Next Steps for Team:**
1. Review Phase 1 recommendations
2. Prioritize based on trading workflow impact
3. Prototype hypothesis verification node
4. Define trade outcome schema for episodic memory

---

*End of Assessment*
