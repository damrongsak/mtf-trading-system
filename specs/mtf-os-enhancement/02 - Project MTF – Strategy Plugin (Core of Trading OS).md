> **Project MTF – Strategy Plugin (Core of Trading OS)**
>
> * integration กับ **production-grade agentic AI trading system**

ผมจัดให้เป็นระดับที่

* อ่านแล้ว “เห็นระบบ”
* เขียนโค้ดตามได้
* ใช้เป็นสัญญาระหว่าง research / engineering / AI ได้จริง

---

# 📘 Spec-Driven Development (SDD)

## Project: MTF – Strategy Plugin & Trading OS Core

---

## 1. Spec Metadata

```yaml
spec_name: MTF_Strategy_Plugin_Spec
version: 1.0.0
status: draft
owner: MTF Core Team
created_at: 2025-12-19
last_updated: 2025-12-19

scope:
  - Strategy Plugin Architecture
  - Feature / State / Decision separation
  - AI Agent integration
  - Backtest & Paper Trading compatibility
```

---

## 2. Problem Statement

ตลาดการเงินไม่ล้มเหลวเพราะ “ขาด indicator”
แต่ล้มเหลวเพราะ:

* logic ปนกันระหว่าง signal / risk / execution
* กลยุทธ์อธิบายไม่ได้
* AI ถูกใช้แบบ black box
* backtest กับ production ไม่เหมือนกัน

**MTF ถูกสร้างเพื่อแก้ปัญหานี้**

---

## 3. Design Philosophy (Non-Negotiable)

### 3.1 Core Principles

* Strategy ≠ Indicator
* Strategy ≠ Execution
* AI ≠ Decision Maker
* Risk overrides everything
* Survival > Profit

### 3.2 Mental Model

> **MTF = Trading Operating System**
> Strategy = Plugin
> AI = Advisor
> Risk = Kernel

---

## 4. High-Level Architecture (5 Layers)

```text
┌──────────────────────────────┐
│ Layer 5: Agentic Intelligence│
├──────────────────────────────┤
│ Layer 4: Risk & Capital      │
├──────────────────────────────┤
│ Layer 3: Execution Context   │
├──────────────────────────────┤
│ Layer 2: Structure           │
├──────────────────────────────┤
│ Layer 1: Probability         │
└──────────────────────────────┘
```

---

## 5. Layer Responsibilities (Explicit)

### Layer 1 — Probability Layer

**Purpose:** กำหนดกรอบความเป็นไปได้ของราคา

* Input: log-return history
* Methods:

  * Block Bootstrap
  * Monte Carlo (90-day horizon)
* Output:

  * p10 / p50 / p90 (min & max)
  * Empirical price distribution

❌ No direction
❌ No signal
❌ No execution

---

### Layer 2 — Structure Layer

**Purpose:** หา structural advantage ของตลาด

* Grid construction:

  * spacing = 0.5 × ATR(30)
  * range = [p10_min, p90_max]
* Open Interest:

  * OI density
  * OI nodes / gaps
  * OI thickness score

Output:

* GridIndex (distance from mean)
* Structural zones

---

### Layer 3 — Execution Context Layer

**Purpose:** อนุญาตหรือปฏิเสธการ execute

* Liquidity sweep
* CHoCH
* Order Block / FVG

Output:

* execution_allowed: true/false
* execution_quality: A / B / Reject

---

### Layer 4 — Risk & Capital Layer

**Purpose:** คุมการอยู่รอดของระบบ

* ATR-normalized stop
* Position sizing:

  * f(GridIndex, OI density, Macro bias)
* Exposure caps
* Kill switch

⚠️ Overrides all other layers

---

### Layer 5 — Agentic Intelligence Layer

**Purpose:** Decision intelligence (not execution)

* Multi-agent orchestration
* RAG over:

  * market summaries
  * strategy playbooks
  * historical trades
* Output:

  * recommendation
  * rationale
  * confidence score

❌ Cannot place trades
❌ Cannot override risk

---

## 6. Core Abstractions

### 6.1 Feature

```yaml
Feature:
  name: string
  layer: Probability | Structure | Execution | Risk
  value: float | categorical | vector
  normalized: boolean
  timestamp: datetime
```

---

### 6.2 MarketState (Single Source of Truth)

```yaml
MarketState:
  probability:
    price_distribution:
      p10: float
      p50: float
      p90: float

  structure:
    grid_index: int
    oi_density: float
    oi_thickness: A | B | Thin

  execution:
    liquidity_sweep: boolean
    choch: boolean
    execution_quality: A | B | Reject

  risk:
    atr: float
    max_position_size: float
    exposure_used: float
```

---

## 7. Strategy Plugin Interface (CORE)

### 7.1 Strategy Contract

```yaml
StrategyPlugin:
  name: string
  version: string

  inputs:
    - MarketState
    - AgentRecommendation (optional)

  outputs:
    - TradeDecision
```

---

### 7.2 TradeDecision Schema

```yaml
TradeDecision:
  action: LONG | SHORT | NO_TRADE
  size_modifier: float   # bounded by Risk Layer
  entry_zone: GridIndex | null
  exit_policy: policy_id
  rationale: string
```

---

### 7.3 Strategy Constraints

Strategy:

* ❌ cannot compute features
* ❌ cannot access raw data
* ❌ cannot override risk
* ❌ cannot store state across time

Strategy must be:

* deterministic
* replayable
* auditable

---

## 8. AI Agent Integration Spec

```yaml
AgentRecommendation:
  summary: string
  supporting_facts:
    - feature_reference
    - historical_analogy
  confidence: 0.0 – 1.0
  model_version: string
  prompt_version: string
```

AI output is:

* advisory only
* fully logged
* versioned

---

## 9. Evaluation & Logging Requirements

### Mandatory Logging

* MarketState snapshot
* Strategy decision
* AI recommendation (if any)
* Risk overrides
* Final execution outcome

### Evaluation Pipelines

* Backtest
* Paper trading
* Strategy vs AI delta analysis
* Survival metrics (drawdown, tail risk)

---

## 10. Definition of Done (DoD)

A Strategy Plugin is **DONE** when:

* [ ] Runs on backtest & paper trading
* [ ] Produces identical result on replay
* [ ] Risk layer can override it
* [ ] AI can be removed without breaking system
* [ ] Decisions are explainable post-mortem

---

## 11. Final Statement (Design Truth)

> **MTF is not a strategy factory**
> **It is a system that prevents bad strategies from killing capital**
>
> Profits are optional
> Survival is mandatory

