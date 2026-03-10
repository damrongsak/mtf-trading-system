# MTF Olympus: AI Analyst (v2.9)

The **AI Analyst** is the institutional-grade "Market Brain" of the MTF Olympus system. It utilizes **Google Gemini 2.5 (Pro/Flash)** and **OpenRouter (Claude 3.5)** within an **Agentic RAG (LangGraph)** architecture to provide structural market mapping, cross-service stability observation, and automated strategy planning with institutional safety guards.

## 🏗️ Agentic Architecture (Dynamic Topology)

The service orchestrates complex reasoning flows through a multi-node Directed Acyclic Graph (DAG) with **Dynamic Topology** that adjusts based on the severity of the market event.

```mermaid
graph TD
    subgraph Input["Input Processing"]
        USR[User Query] --> OPT[Query Optimizer]
        OPT --> SEV{Severity Classifier}
    end

    subgraph Reasoning["Reasoning Engine"]
        SEV -->|ROUTINE| RAG[RAG Node]
        SEV -->|VOLATILITY| SENT[Sentinel Node]
        SEV -->|CRISIS| SENT
        
        RAG --> SYN[Synthesis]
        SENT -->|Approved| DEC[Decomposition]
        SENT -->|Rejected| GEN[Generator]
        
        DEC --> RET[Knowledge Retrieval]
        RET --> REA[CoT Reasoning]
    end

    subgraph Action["Tool Execution"]
        REA --> TS[Tool Selection]
        SYN --> MW[Memory Write]
        TS --> EX[Execute Tools]
        EX --> SUM[Summarizer]
        SUM --> TS
    end

    subgraph Safety["Institutional Protection"]
        TS -->|Proposed Trade| GATE[Economic Sanity Gate]
        GATE -->|Violated| GEN
        GATE -->|Cleared| CON[Consensus Layer]
        CON -->|Disagree/Fail| GEN
        CON -->|Dual-Agree| EX
    end

    subgraph Loop["Validation & Feedback"]
        TS -->|Done| GEN
        GEN --> EVA{Evaluator}
        EVA -->|Iterate| DEC
        EVA -->|Satisfactory| MW
        MW --> END((Response))
    end
```

## 🎯 Core Capabilities

- **Dynamic Topology Routing**: Automatically escalates to `CRISIS` mode for live execution requests, triggering the dual-model Consensus Layer.
- **Sentinel Node (Adversarial Check)**: Performs logic-conflict detection and hallucination checks on every trade proposal.
- **Economic Sanity Gate**: Hard Python-based risk validation (Max lot, Margin check, SL/TP existence) that cannot be bypassed by LLM hallucinations.
- **Automated Daily Post-Mortem**: A scheduled task (01:00 UTC) that fetches closed trades, extracts "Lessons Learned" using a specialized agent, and injects them into the RAG memory.
- **Consensus Layer with Fallback**: Dual-verification using **Claude 3.5 (OpenRouter)** and **Gemini 2.5 Flash**. Includes automatic fallback to Gemini if OpenRouter is unavailable.
- **Agentic RAG**: Context-aware retrieval from **Qdrant** (Quant Library, Systems Docs, Journals, Lessons Learned).
- **Adaptive News Re-ranking**: Dynamic feedback loop that extracts "Key Drivers" from news and re-ranks subsequent data for faster volatility response.
- **OS-Level Tool Suite**: Direct access to local Shell, Python Interpreter, and Web Reader for autonomous research and data processing.
- **Hybrid Adaptive Memory**: Injects both persistent User Facts and Institutional Lessons Learned into every agent session.
- **Persistent Skill Manager (agentskills.io)**: Allows the agent to discover, load, and execute specialized workflows defined in `SKILL.md` files. Supports both internal and external skill paths.
- **Native Tool Standardization (v2.9)**: All core analytical tools (SMC, OI, Account, Calendar) are implemented as native `BaseTool`s for maximum reliability and strict schema validation.

## 🤖 AI-Agent Operational Guide

To understand or extend the AI Analyst, follow this discovery path:

1.  **Persona & Prompts**: Core behavior in `app/core/prompts.py`.
2.  **Graph Structure**: Node wiring and dynamic routing in `app/agents/strategy_advisor.py`.
3.  **Safety Guards**: Risk logic in `app/agents/sentinel/economic_sanity_gate.py` and `app/agents/sentinel/consensus_layer.py`.
4.  **Learning Tasks**: Background jobs and post-mortem logic in `app/core/scheduler_tasks.py` and `app/agents/post_mortem.py`.

## 🔧 Operational Guide

### Diagnostic CLI & Verification
Probing the system or testing CRISIS flows:
```bash
# General Chat
docker compose exec ai-analyst python3 scripts/chat_cli.py

# Manual Daily Post-Mortem Trigger
docker compose exec ai-analyst python3 tests/manual_post_mortem_run.py

# Crisis Workflow Integration Test
docker compose exec ai-analyst python3 tests/test_crisis_workflow_integration.py
```

### Common Issues & Fixes

| Symptom | Probable Cause | Fix |
| :--- | :--- | :--- |
| **Consensus Failures** | OpenRouter API Down | Check root `.env` for `OPENROUTER_API_KEY`; Verify fallback logs. |
| **Sanity Gate Rejection** | Missing SL/TP or Lot > 0.1 | Ensure trade proposals follow institutional risk limits. |
| **Serialization Errors** | UUID/Decimal in trades | Use `json_util` or string conversion in `scheduler_tasks.py`. |

## 🗄️ Managed Knowledge (Qdrant)

| Collection | Data Source | Purpose |
| :--- | :--- | :--- |
| `lesson_learned` | Daily Post-Mortem | Self-learning from past mistakes/wins |
| `user_memory` | Chat History | Long-term user preference tracking |
| `system_docs` | Specs/Codebase | Ensuring SDD compliance in agent reasoning |
| `quant_library` | PDFs/Books | Professional technical analysis context |

## 📂 Directory Structure

```text
app/
├── agents/            # LangGraph nodes, Sentinel, Post-Mortem, & Consensus
│   └── sentinel/      # Safety gate and multi-model consensus logic
├── core/              # Persona prompts, Pydantic schemas, & Scheduler
├── services/          # Model clients (Gemini/OpenRouter), RAG, & Memory
├── tools/             # Standardized Native BaseTools (SMC, OI, etc.)
├── skills/            # Internal persistent skills (SKILL.md Physical Skeleton)
└── main.py            # FastAPI entrypoint & Scheduler init
```

## 📚 Dynamic Skills (agentskills.io Standard)

The agent dynamically discovers skills from two primary locations:
1.  **Internal**: `services/ai-analyst/skills/`
2.  **External/Examples**: `example/skills/`

Each skill follows the **Physical Skeleton** standard:
- `SKILL.md`: Frontmatter + Instructions.
- `references/`: Contextual data injected into sub-agents.
- `scripts/`: Executable assets.
```

## 🛠️ Development

Uses `uv` for lightning-fast dependency management.

```bash
# Install environment
uv sync

# Run locally
uv run uvicorn app.main:app --reload --port 8000
```

---
**MTF Olympus** | *Institutional Alpha at Scale*
