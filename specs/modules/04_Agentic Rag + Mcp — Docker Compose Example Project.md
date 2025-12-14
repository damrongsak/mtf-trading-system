# Spec-Driven Development (SDD)

## Agentic RAG Integration for MTF Trading System

---

## 0. Purpose of This Specification

This document defines **clear, testable specifications** for extending the existing **MTF Trading System** with **Agentic RAG + MCP**.

The goal is **not** to build a smarter predictor, but to build **auditable, risk-aware, decision-support agents** suitable for real trading environments.

This spec is written to support:

* Incremental development
* Agent-by-agent rollout
* Production-grade reasoning systems

---

## 1. System Design Principles (Non-Negotiable)

1. **Agents do not predict markets**
   Agents reason about rules, risk, context, and consistency.

2. **Every agent decision must be explainable**
   No opaque "because the model said so" outputs.

3. **Knowledge ≠ Authority**
   RAG provides information. Agents decide whether and how to use it.

4. **All external systems are accessed via MCP**
   No direct DB or API calls inside agent logic.

5. **Self-verification is mandatory**
   No agent output is accepted without internal validation.

---

## 2. Target Architecture (Logical)

```
User / System Event
        ↓
Agent Orchestrator
        ↓
Planning Agent (Intent + Scope)
        ↓
Context Assembly (RAG + MCP)
        ↓
Reasoning Agent
        ↓
Verification Agent
        ↓
Approved Output / Action
```

---

## 3. MCP Contracts (Core Interfaces)

### 3.1 MCP-Market

**Purpose**: Provide market context and event risk

**Endpoints**:

* `GET /calendar`
* `GET /volatility-regime`
* `GET /session-info`

**Returns**:

* Structured JSON only
* No natural language

---

### 3.2 MCP-Portfolio

**Purpose**: Portfolio state awareness

**Endpoints**:

* `GET /positions`
* `GET /exposure`
* `GET /drawdown`

---

### 3.3 MCP-Strategy

**Purpose**: Canonical strategy rules

**Endpoints**:

* `GET /rules`
* `GET /constraints`

---

### 3.4 MCP-Journal

**Purpose**: Trade history and outcomes

**Endpoints**:

* `GET /trades`
* `GET /performance`

---

## 4. Agent Specifications

---

### 4.1 Trade Review Agent (Post-Trade)

**Trigger**:

* Trade closed event

**Inputs**:

* Trade execution data
* Strategy rules (MCP-Strategy)
* Market context (MCP-Market)

**Responsibilities**:

* Validate rule adherence
* Identify execution errors
* Classify outcome: skill vs luck vs violation

**Output Schema**:

```json
{
  "rule_compliance": true,
  "violations": [],
  "context_alignment": "valid",
  "confidence_level": "high",
  "explanation": "..."
}
```

**Verification Rules**:

* All claims must reference a rule or data source
* Opinions without evidence are rejected

---

### 4.2 Pre-Trade Risk Gate Agent

**Trigger**:

* Strategy signals intent to open position

**Inputs**:

* Proposed trade
* Portfolio exposure
* Market regime

**Decision Space**:

* APPROVE
* REJECT
* DEFER

**Constraints**:

* Cannot modify trade parameters
* Can only allow or block

**Output Schema**:

```json
{
  "decision": "REJECT",
  "reason_codes": ["HIGH_CORRELATION", "EVENT_RISK"],
  "evidence": ["MCP-Market.calendar", "MCP-Portfolio.exposure"]
}
```

---

### 4.3 Strategy Reasoning Explainer Agent

**Trigger**:

* Trade approved or executed

**Responsibilities**:

* Produce human-readable rationale
* Reference exact rules and market structure

**Forbidden Behavior**:

* Market prediction
* Emotional or persuasive language

---

### 4.4 Research Copilot Agent

**Trigger**:

* Manual request or scheduled scan

**Responsibilities**:

* Summarize research materials
* Map concepts to existing strategies
* Explicitly state uncertainty

**Output Must Include**:

* Applicability score
* Risk assumptions

---

## 5. RAG Knowledge Domains

Each domain is indexed separately:

* Strategy rules
* Market structure theory
* Risk management doctrine
* Historical trade patterns

Cross-domain reasoning is agent-driven, not retriever-driven.

---

## 6. Verification & Guardrails

All agents must pass:

* Evidence completeness check
* Contradiction scan
* Scope compliance

Failed verification → output discarded

---

## 7. Observability Requirements

Mandatory logs:

* Agent plan
* MCP calls
* Context used
* Verification outcome

Purpose:

* Auditability
* Model evaluation
* Regulatory readiness

---

## 8. Non-Goals (Explicit)

This system will NOT:

* Predict price direction
* Optimize strategy parameters automatically
* Replace human decision-making

---

## 9. Development Phasing

Phase 1:

* Trade Review Agent
* MCP-Journal + MCP-Strategy

Phase 2:

* Pre-Trade Risk Gate
* MCP-Market + MCP-Portfolio

Phase 3:

* Strategy Explainer
* Research Copilot

---

## 10. Definition of Done (DoD)

An agent is considered production-ready when:

* All decisions are reproducible
* All outputs are verifiable
* Failure modes are explicit
* Agent can say "I do not know"

---

## Final Note

This specification treats AI agents as **risk-bearing system components**, not features.

If an agent cannot justify its decision,
it does not belong in a trading system.
