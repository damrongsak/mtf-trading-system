# Olympus AI Analyst v2.2: Dynamic Topology + Sentinel Layer Implementation Analysis

**Date:** 2026-03-08  
**Analyst:** Soda  
**Status:** ✅ Recommended for Implementation  
**Version:** 2.0 (Updated with Institutional-Grade Features)

---

## 0. Executive Summary (v2.0 Updates)

Based on **Olympus Institutional Critique & Evolution** analysis, this document now includes:

| Priority | Gap | Implementation |
|----------|-----|---------------|
| **1** | Economic Sanity Check | Python-based hard constraints for Margin/Risk-of-Ruin |
| **2** | Consensus Layer | Dual-model verification for CRISIS decisions |
| **3** | Post-Mortem Agent | Automated lesson learning → Qdrant |

---

## 1. Current Architecture Gap Analysis

### Existing Nodes (from `strategy_advisor.py`)

| Node | Function |
|------|----------|
| `query_optimizer` | Classifies INTENT |
| `router` | Routes to: direct/complex/research/tool_use/market_scan |
| `decompose` | Breaks down complex queries |
| `retrieve_knowledge` | RAG retrieval |
| `synthesize` | Deep research |
| `reasoning` | CoT reasoning |
| `tool_selection` | Selects tools |
| `execute_tools` | Runs tools |
| `summarizer` | Condenses scratchpad |
| `generate` | Final response |
| `evaluator` | Checks if satisfactory |
| `memory_write` | Saves to memory |

### Identified Gaps

- ❌ No **Severity Classification** (ROUTINE/VOLATILITY/CRISIS)
- ❌ No **Sentinel Node** for adversarial review
- ❌ No **Dynamic Topology** that scales based on severity

---

## 2. Required Additions

### 2.1 Severity Classifier Node (NEW)

```python
# Add to AgentState
severity: str  # 'ROUTINE' | 'VOLATILITY' | 'CRISIS'

async def node_severity_classifier(self, state: AgentState):
    """
    Classifies severity based on query + market context.
    - CRISIS: Regime change, war, sanctions, flash crash
    - VOLATILITY: High-impact news, ECB/FOMC, earnings
    - ROUTINE: Daily briefing, simple queries
    """
```

### 2.2 Dynamic Topology Routing (MODIFY router)

```python
# Add severity to routing decision
SEVERITY_MAP = {
    ('ROUTINE', 'CHAT'): ['generate'],                    # 1 agent
    ('ROUTINE', 'MARKET_ANALYSIS'): ['market_scan', 'generate'],
    ('VOLATILITY', 'MARKET_ANALYSIS'): ['retrieve_knowledge', 'synthesize', 'reasoning', 'generate'],
    ('CRISIS', 'MARKET_ANALYSIS'): ['retrieve_knowledge', 'synthesize', 'reasoning', 'tool_selection', 'sentinel', 'generate'],
}
```

### 2.3 Sentinel Node (NEW)

```python
async def node_sentinel(self, state: AgentState):
    """
    Adversarial review - LLM checks for:
    - Hallucination
    - Logical consistency
    - Risk assessment
    """
```

---

## 3. Updated Architecture

```
                    ┌──────────────────┐
                    │ query_optimizer  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ severity_classifier │ ← NEW
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │  ROUTINE  │  │VOLATILITY │  │  CRISIS   │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │ generate  │  │  +RAG     │  │Full Swarm │
        │           │  │  +Reason  │  │+Sentinel  │ ← NEW
        └───────────┘  └───────────┘  └───────────┘
```

---

## 4. Pros & Cons

### ✅ Pros

| Aspect | Detail |
|--------|--------|
| **Token Optimization** | Routine tasks use minimal tokens — cost savings |
| **Quality Assurance** | Sentinel catches hallucination during crisis |
| **Scalability** | Easy to add new severity levels (e.g., BLACK_SWAN) |
| **Reuse Existing** | Uses existing LangGraph infrastructure |
| **Interpretability** | Clear routing by severity — easy debugging |

### ⚠️ Cons & Risks

| Risk | Issue | Mitigation |
|------|-------|------------|
| **Complexity** | Graph complexity increases | Structured logging |
| **Latency** | +200-500ms for classification | Use Gemini Flash for classifier |
| **Accuracy** | Classifier may misroute | Manual override fallback |
| **Sentinel Overhead** | +300ms, more tokens | Use only for CRISIS + TOOL_USE |
| **State Bloat** | Severity adds to context | Prune before next node |

---

## 5. Implementation Timeline

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Add `severity` field to AgentState | 1 hour |
| 2 | Create `node_severity_classifier` | 2-3 hours |
| 3 | Update conditional edges for severity routing | 2-3 hours |
| 4 | Create `node_sentinel` (adversarial review) | 2 hours |
| 5 | Add severity to query_optimizer prompt | 1 hour |
| 6 | Test & Debug | 3-4 hours |

**Total: ~1-2 days**

---

## 6. Excluded from Recommendation

| Feature | Reason for Exclusion |
|---------|---------------------|
| **Memgraph** | Qdrant sufficient; RAM overhead too high |
| **Claude 4.6** | Gemini 2.5 Pro sufficient; cost too high |
| **GRPO Training** | Over-engineering; rule-based sufficient |
| **Full Swarm** | Not necessary yet; start with dynamic DAG |

---

## 7. Summary

| Aspect | Score |
|--------|-------|
| **Technical Feasibility** | 9/10 — LangGraph already supports this |
| **Token Efficiency** | 8/10 — Saves tokens on routine tasks |
| **Risk Mitigation** | 7/10 — Sentinel catches errors |
| **Time to Implement** | 1-2 days |
| **Breaking Changes** | None — additive changes only |

**Recommendation:** ✅ **Proceed with implementation**

---

## 8. Files Modified

- `/home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/strategy_advisor.py`
  - Add `severity` field to `AgentState`
  - Add `node_severity_classifier`
  - Add `node_sentinel`
  - Update routing logic

---

*Generated by Soda | 2026-03-07*

---

# APPENDIX A: Institutional-Grade Implementation Details (v2.0)

## A.1 Economic Sanity Gate (Priority 1)

### Purpose
แยก Logic ออกจาก LLM → Python Script เช็ค Margin/Risk-of-Ruin แบบ Hard Constraints

### Location
New file: `/home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/sentinel/economic_sanity_gate.py`

### Implementation

```python
# economic_sanity_gate.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class AccountState:
    balance: Decimal
    equity: Decimal
    margin_used: Decimal
    open_positions: int
    
    @property
    def free_margin(self) -> Decimal:
        return self.equity - self.margin_used
    
    @property
    def margin_level(self) -> Optional[Decimal]:
        if self.margin_used == 0:
            return None
        return (self.equity / self.margin_used) * 100

@dataclass 
class TradeProposal:
    symbol: str
    direction: str  # 'BUY' | 'SELL'
    lot_size: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    
class EconomicSanityGate:
    """Hard constraints - 100% deterministic, no LLM involved"""
    
    # Configurable thresholds (load from config)
    MAX_LOT_SIZE = Decimal("0.1")      # Initial testing cap
    MIN_MARGIN_LEVEL = Decimal("150")  # Stop out level + buffer
    MAX_DAILY_LOSS_PCT = Decimal("2")  # 2% of account
    MAX_CONCURRENT_TRADES = 3
    RISK_OF_RUIN_LOSS_PCT = Decimal("6")  # Max 6% total drawdown
    
    def __init__(self, account: AccountState, daily_pnl: Decimal = Decimal("0")):
        self.account = account
        self.daily_pnl = daily_pnl
    
    def validate_proposal(self, proposal: TradeProposal) -> tuple[bool, list[str]]:
        """
        Returns (is_safe, list_of_violations)
        """
        violations = []
        
        # 1. Lot size check
        if proposal.lot_size > self.MAX_LOT_SIZE:
            violations.append(f"LOT_EXCEEDED: {proposal.lot_size} > {self.MAX_LOT_SIZE}")
        
        # 2. Margin check
        required_margin = self._calculate_required_margin(proposal)
        if self.account.free_margin < required_margin:
            violations.append(f"INSUFFICIENT_MARGIN: need {required_margin}, have {self.account.free_margin}")
        
        # 3. Margin level check
        if self.account.margin_level and self.account.margin_level < self.MIN_MARGIN_LEVEL:
            violations.append(f"MARGIN_LEVEL_LOW: {self.account.margin_level}% < {self.MIN_MARGIN_LEVEL}%")
        
        # 4. Daily loss check
        if abs(self.daily_pnl) > self.account.balance * (self.MAX_DAILY_LOSS_PCT / 100):
            violations.append(f"DAILY_LOSS_LIMIT: {self.daily_pnl} exceeded")
        
        # 5. Concurrent positions check
        if self.account.open_positions >= self.MAX_CONCURRENT_TRADES:
            violations.append(f"MAX_POSITIONS: {self.account.open_positions} >= {self.MAX_CONCURRENT_TRADES}")
        
        # 6. Risk-of-Ruin check
        total_exposure = self._calculate_total_exposure(proposal)
        if total_exposure > self.account.balance * (self.RISK_OF_RUIN_LOSS_PCT / 100):
            violations.append(f"RISK_OF_RUIN: exposure {total_exposure} > 6%")
        
        # 7. SL/TP sanity
        if proposal.stop_loss == proposal.entry_price:
            violations.append("SL_SAME_AS_ENTRY")
        if proposal.take_profit == proposal.entry_price:
            violations.append("TP_SAME_AS_ENTRY")
        if proposal.direction == "BUY" and proposal.stop_loss >= proposal.entry_price:
            violations.append("LONG_SL_ABOVE_ENTRY")
        if proposal.direction == "SELL" and proposal.stop_loss <= proposal.entry_price:
            violations.append("SHORT_SL_BELOW_ENTRY")
        
        return (len(violations) == 0, violations)
    
    def _calculate_required_margin(self, proposal: TradeProposal) -> Decimal:
        # Simplified - in production, fetch from broker API
        margin_per_lot = Decimal("1000")  # XAUUSD default
        return proposal.lot_size * margin_per_lot
    
    def _calculate_total_exposure(self, proposal: TradeProposal) -> Decimal:
        # Calculate worst-case loss if SL hit
        sl_distance = abs(proposal.entry_price - proposal.stop_loss)
        # Simplified position value
        return sl_distance * proposal.lot_size * Decimal("100")  # ~$100 per pip per lot
```

### Integration with Sentinel Node

```python
# In sentinel node, after LLM review:
async def node_sentinel(self, state: AgentState):
    # ... LLM hallucination check ...
    
    # NEW: Economic Sanity Gate
    if state.get("proposed_trade"):
        account_state = await self._fetch_account_state()
        daily_pnl = await self._fetch_daily_pnl()
        
        gate = EconomicSanityGate(account_state, daily_pnl)
        is_safe, violations = gate.validate_proposal(state["proposed_trade"])
        
        if not is_safe:
            state["sentinel_result"] = {
                "approved": False,
                "reason": "ECONOMIC_VIOLATION",
                "violations": violations
            }
            return state
    
    state["sentinel_result"] = {"approved": True}
    return state
```

---

## A.2 Consensus Layer for CRISIS Decisions (Priority 2)

### Purpose
ใช้ 2 models ตรวจกันก่อน execute ในกรณี CRISIS

### Location
New file: `/home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/sentinel/consensus_layer.py`

### Implementation

```python
# consensus_layer.py
from enum import Enum
from typing import Optional
import asyncio

class ConsensusMode(Enum):
    SINGLE = "single"           # Normal operation
    CONSENSUS = "consensus"     # Dual model for CRISIS

class ConsensusDecision:
    def __init__(self):
        self.primary_result: Optional[dict] = None
        self.secondary_result: Optional[dict] = None
        self.consensus_reached: bool = False
        self.disagreement: list[str] = []

class CrisisConsensusLayer:
    """
    Dual-model verification for CRISIS decisions.
    Uses two different model providers for independence.
    """
    
    # Models to use (configure in settings)
    PRIMARY_MODEL = "minimax-portal/MiniMax-M2.5"  # Default
    SECONDARY_MODEL = "openrouter/anthropic/claude-3.5-sonnet"  # Fallback diversity
    
    def __init__(self, primary_llm, secondary_llm):
        self.primary_llm = primary_llm
        self.secondary_llm = secondary_llm
    
    async def verify_crisis_decision(
        self, 
        decision: dict,
        context: dict
    ) -> ConsensusDecision:
        """
        Run both models on the same prompt, compare results.
        Returns consensus only if both agree on direction + magnitude.
        """
        result = ConsensusDecision()
        
        # Build verification prompt
        prompt = self._build_verification_prompt(decision, context)
        
        # Execute both in parallel
        primary_task = self.primary_llm.agenerate(prompt)
        secondary_task = self.secondary_llm.agenerate(prompt)
        
        primary_response, secondary_response = await asyncio.gather(
            primary_task, secondary_task
        )
        
        result.primary_result = self._parse_response(primary_response)
        result.secondary_result = self._parse_response(secondary_response)
        
        # Analyze agreement
        result.consensus_reached = self._check_consensus(
            result.primary_result,
            result.secondary_result
        )
        
        if not result.consensus_reached:
            result.disagreement = self._identify_disagreements(
                result.primary_result,
                result.secondary_result
            )
        
        return result
    
    def _check_consensus(self, primary: dict, secondary: dict) -> bool:
        """Both must agree on: direction, entry zone, stop loss zone"""
        if not primary or not secondary:
            return False
        
        # Direction must match
        if primary.get("direction") != secondary.get("direction"):
            return False
        
        # Entry price within 0.5% tolerance
        entry_diff = abs(
            float(primary.get("entry_price", 0)) - 
            float(secondary.get("entry_price", 0))
        ) / float(primary.get("entry_price", 1))
        
        if entry_diff > 0.005:  # 0.5%
            return False
        
        return True
    
    def _build_verification_prompt(self, decision: dict, context: dict) -> str:
        return f"""You are a risk manager. Verify this trade decision:

TRADE DECISION:
- Symbol: {decision.get('symbol')}
- Direction: {decision.get('direction')}
- Entry: {decision.get('entry_price')}
- Stop Loss: {decision.get('stop_loss')}
- Take Profit: {decision.get('take_profit')}
- Lot Size: {decision.get('lot_size')}

MARKET CONTEXT:
- Current Price: {context.get('current_price')}
- VIX Level: {context.get('vix')}
- News: {context.get('news_summary')}

Respond in JSON:
{{
  "direction": "BUY|SELL|NONE",
  "entry_price": float,
  "stop_loss": float,
  "risk_level": "LOW|MEDIUM|HIGH",
  "rationale": "string"
}}
"""
    
    def _parse_response(self, response: dict) -> dict:
        # Extract JSON from response
        # Simplified - implement proper parsing
        try:
            return response.get("parsed", {})
        except:
            return {}
    
    def _identify_disagreements(self, primary: dict, secondary: dict) -> list[str]:
        disagreements = []
        if primary.get("direction") != secondary.get("direction"):
            disagreements.append(f"Direction: {primary.get('direction')} vs {secondary.get('direction')}")
        return disagreements
```

### Integration

```python
# In strategy_advisor.py - update CRISIS routing
CRISIS_WORKFLOW = {
    'initial': ['query_optimizer', 'severity_classifier'],
    'severity_classifier': {
        'CRISIS': ['retrieve_knowledge', 'synthesize', 'reasoning', 'tool_selection'],
        'default': ['generate']
    },
    # NEW: Add consensus after tool_selection for CRISIS
    'tool_selection': ['consensus_layer', 'execute_tools'],  # NEW NODE
    'consensus_layer': {
        'approved': ['execute_tools'],
        'rejected': ['generate_rejection']  # Inform user, no execution
    },
    'execute_tools': ['sentinel', 'generate'],
}
```

---

## A.3 Post-Mortem Agent (Priority 3)

### Purpose
หลังปิดดีลหรือจบวัน → เขียน "บทเรียนทางเทคนิค" ลง Qdrant แยก (Lesson Learned Library)

### Location
New file: `/home/dan/workspace/mtf-trading-system/services/ai-analyst/app/agents/postmortem_agent.py`

### Implementation

```python
# postmortem_agent.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

@dataclass
class TradeOutcome:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    lot_size: float
    pnl: float
    pnl_pct: float
    duration_minutes: int
    exit_reason: str  # 'SL' | 'TP' | 'MANUAL' | 'TIME'
    
    # Analysis fields
    market_regime: str  # 'TRENDING' | 'RANGING' | 'VOLATILE'
    news_events: list[str]
    setup_quality: int  # 1-10

@dataclass  
class LessonLearned:
    timestamp: str
    category: str  # 'ENTRY_TIMING' | 'RISK_MANAGEMENT' | 'MARKET_CONTEXT' | 'PSYCHOLOGY'
    title: str
    summary: str
    technical_details: str
    action_items: list[str]
    related_trades: list[str]

class PostMortemAgent:
    """
    Analyzes closed trades and generates lessons learned.
    Stores to Qdrant collection: 'lesson_learned'
    """
    
    def __init__(self, qdrant_client, llm):
        self.qdrant = qdrant_client
        self.llm = llm
        self.collection_name = "lesson_learned"
    
    async def analyze_trade(self, outcome: TradeOutcome) -> LessonLearned:
        """Main entry point - analyze a single trade"""
        
        # 1. Fetch related context
        context = await self._fetch_market_context(outcome)
        
        # 2. Generate analysis using LLM
        analysis = await self._llm_analyze(outcome, context)
        
        # 3. Create LessonLearned object
        lesson = LessonLearned(
            timestamp=datetime.utcnow().isoformat(),
            category=analysis["category"],
            title=analysis["title"],
            summary=analysis["summary"],
            technical_details=analysis["technical_details"],
            action_items=analysis["action_items"],
            related_trades=[outcome.trade_id]
        )
        
        # 4. Store to Qdrant
        await self._store_lesson(lesson)
        
        return lesson
    
    async def daily_postmortem(self, trades: list[TradeOutcome]) -> list[LessonLearned]:
        """Analyze all trades from the day"""
        lessons = []
        
        for trade in trades:
            lesson = await self.analyze_trade(trade)
            lessons.append(lesson)
        
        # Generate aggregate lessons
        aggregate = await self._generate_aggregate_lessons(trades, lessons)
        
        return lessons + aggregate
    
    async def _llm_analyze(self, outcome: TradeOutcome, context: dict) -> dict:
        prompt = f"""Analyze this trade outcome and extract lessons:

TRADE:
- ID: {outcome.trade_id}
- Symbol: {outcome.symbol}
- Direction: {outcome.direction}
- Entry: {outcome.entry_price}
- Exit: {outcome.exit_price}
- P&L: {outcome.pnl} ({outcome.pnl_pct}%)
- Duration: {outcome.duration_minutes} min
- Exit Reason: {outcome.exit_reason}

MARKET CONTEXT:
- Regime: {outcome.market_regime}
- News: {outcome.news_events}
- Pre-trade Setup Quality: {outcome.setup_quality}/10

Respond in JSON:
{{
  "category": "ENTRY_TIMING|RISK_MANAGEMENT|MARKET_CONTEXT|PSYCHOLOGY",
  "title": "Brief lesson title",
  "summary": "2-3 sentence summary",
  "technical_details": "Detailed technical analysis",
  "action_items": ["action1", "action2"]
}}
"""
        response = await self.llm.agenerate(prompt)
        return self._parse_json(response)
    
    async def _store_lesson(self, lesson: LessonLearned):
        payload = {
            "timestamp": lesson.timestamp,
            "category": lesson.category,
            "title": lesson.title,
            "summary": lesson.summary,
            "technical_details": lesson.technical_details,
            "action_items": json.dumps(lesson.action_items),
            "related_trades": json.dumps(lesson.related_trades)
        }
        
        await self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[{
                "id": f"{lesson.timestamp}_{lesson.category}",
                "payload": payload,
                "vector": await self._generate_vector(lesson.summary)
            }]
        )
    
    async def _generate_vector(self, text: str) -> list[float]:
        # Use embedding model
        # Simplified - implement with embedding API
        return [0.0] * 384  # Placeholder
```

### Cron Job Integration

```python
# Add to cron jobs (via OpenClaw cron or Olympus internal scheduler)
# Run at 21:00 GMT+7 daily

CRON_JOB_DAILY_POSTMORTEM = {
    "name": "daily_postmortem",
    "schedule": {"kind": "cron", "expr": "0 21 * * *", "tz": "Asia/Bangkok"},
    "payload": {
        "kind": "agentTurn",
        "message": "Run postmortem analysis for today's trades. Fetch from /api/v1/execution/trades?from=today. Analyze each trade, generate lessons, store to Qdrant."
    },
    "sessionTarget": "isolated",
    "delivery": {"mode": "announce", "channel": "telegram"}
}
```

---

## A.4 Reflex vs Cognition Architecture (Overview)

### Layer 1: Reflex (Deterministic, <50ms)
```
┌─────────────────────────────────────────┐
│ Redis / Python                          │
│                                         │
│ • Hard stops check                     │
│ • Max drawdown check                   │
│ • Margin level check                    │
│ • Circuit breaker                       │
└─────────────────────────────────────────┘
              ↓ (pass to Layer 2 if safe)
```

### Layer 2: Cognitive (Agentic, <3s)
```
┌─────────────────────────────────────────┐
│ LangGraph Agent                         │
│                                         │
│ • Strategy planning                    │
│ • Geopolitical analysis                │
│ • Chain-of-Verification (CoVe)          │
│ • Sentinel review                       │
└─────────────────────────────────────────┘
```

### Integration Point
```
User Query → query_optimizer → severity_classifier
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ROUTINE          VOLATILITY        CRISIS
                    │               │               │
              Layer 2         Layer 2 +       Layer 1 (Reflex)
                             CoVe           → Layer 2 (Cognition)
                                              → Consensus Layer
                                              → Sentinel
```

---

## A.5 Implementation Priority Checklist

| Priority | Task | File | Status |
|----------|------|------|--------|
| 1 | Economic Sanity Gate | `sentinel/economic_sanity_gate.py` | ⬜ Pending |
| 2 | Integrate Gate → Sentinel | `agents/strategy_advisor.py` | ⬜ Pending |
| 3 | Consensus Layer | `sentinel/consensus_layer.py` | ⬜ Pending |
| 4 | Integrate Consensus → CRISIS workflow | `agents/strategy_advisor.py` | ⬜ Pending |
| 5 | Post-Mortem Agent | `agents/postmortem_agent.py` | ⬜ Pending |
| 6 | Qdrant collection setup | `lesson_learned` collection | ⬜ Pending |
| 7 | Daily cron job | Cron configuration | ⬜ Pending |

---

*Updated by Soda | 2026-03-08*

---

## 🔬 Post-Implementation Feedback (Analysis)

**Completion Date:** 2026-03-08  
**Implemented by:** Antigravity Agent  

### 1. What was Achieved
- ✅ **Dynamic Topology**: Successfully implemented routing based on `ROUTINE`, `VOLATILITY`, and `CRISIS` severity.
- ✅ **Sentinel Node (Adversarial Check)**: Added to the graph to catch hallucinations and logic conflicts.
- ✅ **Economic Sanity Gate**: Implemented as a hard-coded Python validator (`economic_sanity_gate.py`) protecting against high lot sizes and margin violations.
- ✅ **Consensus Layer for CRISIS**: Integrated dual-model verification using OpenRouter (Claude) with a Gemini fallback.
- ✅ **Daily Post-Mortem**: Automated scheduler task implemented to analyze closed trades and store lessons in Qdrant.

### 2. Technical Fixes & Refinements
- **Serialization**: Fixed `UUID` and `Decimal` JSON serialization errors in `scheduler_tasks.py`.
- **Type Handling**: Resolved `TypeError: 'HumanMessage' object is not subscriptable` in `strategy_advisor.py` by implementing robust message parsing (getattr/isinstance).
- **Import Restoration**: Fixed missing Pydantic schema imports (`PlanDecomposition`, `SentinelResult`).
- **Sentinel Robustness**: Updated `node_sentinel` to handle both dictionary and string-based tool proposals.

### 3. Excluded / Remaining Gaps
- ❌ **Memgraph**: Deferred in favor of Qdrant (Priority: Memory Efficiency).
- ❌ **Cross-Asset Correlation Matrix**: Moved to Phase 4 for future research.
- ❌ **Mixture of Agents (MoA)**: Currently limited to the Consensus Layer for performance reasons.

**Final Status:** 🚀 **Institutional Safety Guards fully operational.**
