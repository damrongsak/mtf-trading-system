# **MTF Olympus (v2.2) \- The Hybrid Evolution**

**Status:** 🏗️ Phase 5: Strategy Execution (Hybrid Model-First Integration)

**Architecture:** LLM-Generated Bayesian Networks \+ Minimax Regret

**License:** [Apache 2.0](https://www.google.com/search?q=LICENSE)

# **Start with Why: The Hybrid Evolution**

Project Olympus has evolved. Recognizing that LLMs are brilliant at context but unreliable at math, v2.2 introduces the **"Model-First Hybrid"** architecture. We are no longer asking an AI to "trade" for us; we are using AI as an **Intelligent Structural Architect** to build causal models that a high-precision Bayesian engine then executes.

**We don't trust AI with the math. We trust it with the "Vibe".**

## **🏗️ The 5-Layer Hybrid Stack**

Olympus integrates the latest research in **Transparent Trading** by decoupling qualitative reasoning from quantitative execution across our five existing layers:

| Layer | Hybrid Role | Implementation |
| :---- | :---- | :---- |
| **L1: Probability** | **Regime Ingestion** | Tick streamer \+ historical data tagged by "Market Regime". |
| **L2: Structure** | **The Architect** | LLM (Gemini 2.5 Flash) generates a Directed Acyclic Graph (DAG). |
| **L3: Context** | **The Bayesian Engine** | pgmpy populates the DAG with L1 data to calculate ![][image1]. |
| **L4: Risk** | **Minimax Citadel** | Decision engine that minimizes "Maximum Regret" based on L3 probabilities. |
| **L5: Intelligence** | **The Critic** | Mental Hand History (MHH) analyzes DAG failures for continuous learning. |

## **🚀 Key Features**

### **1\. The Causal Architect (L2)**

Instead of black-box signals, the system generates a **Transparent Causal Map** for every trade. It identifies how macro trends, technical indicators, and sentiment influence risk.

* **Result:** You see exactly *why* a trade was taken, down to the causal link.

### **2\. Bayesian Inference (L3)**

By using Bayesian Networks, Olympus avoids "Numerical Hallucinations." The system uses deterministic algorithms to calculate probabilities, ensuring that 1 \+ 1 always equals 2, while still accounting for the "soft" factors like market fear.

### **3\. Minimax Regret Citadel (L4)**

Our risk management now plays a "Zero-Sum Game" against the market. By calculating the **Regret Matrix**, Olympus chooses the path (Execute vs. Avoid) that minimizes the maximum potential pain, protecting the portfolio during "Black Swan" events.

### **4\. Mental Hand History (L5)**

The **AI Coach** now performs post-mortem analysis on the causal models. If a trade fails, the Coach detects if the "Architect" was biased or if the market regime shifted, updating the system's structural knowledge base.

## **📂 System Components**

mtf-trading-system/  
├── services/  
│   ├── ai-analyst/         \# L2 Architect (DAG Gen) & L5 Critic (Feedback)  
│   ├── strategy-core/      \# L3 Bayesian Engine (pgmpy) & L1 Data Retrieval  
│   ├── execution/          \# L4 Risk Citadel (Minimax Regret logic)  
│   ├── data-pipeline/      \# L1 Tick Streaming & Regime Tagging  
│   └── api-gateway/        \# Central Routing  
├── specs/                  \# SDD: Updated with Causal Schema (03\_data\_model)  
└── frontend/               \# Next.js Dashboard with Causal Graph Visualization

## **🛠️ Hybrid Workflow**

1. **Tagging:** Data is ingested and tagged with a "Regime" (e.g., *High-Vol Bearish Recovery*).  
2. **Architecting:** ai-analyst generates a JSON-based DAG for the current regime.  
3. **Calibrating:** strategy-core fits historical data to the DAG to create Conditional Probability Tables (CPTs).  
4. **Deciding:** execution service runs the Minimax engine to finalize the trade.  
5. **Learning:** After trade close, the ai-analyst reviews the "Hand History" and updates the causal schema.

## **🧩 Spec-Driven Development (SDD)**

* specs/01\_architecture.md: Updated to include the LLM-Bayesian Hybrid Loop.  
* specs/03\_data\_model.yaml: Added causal\_graphs and bayesian\_trade\_audit tables.  
* specs/10\_implementation\_status.md: Phase 5 \- Strategy Execution is currently **Active**.

## **⚠️ Disclaimer**

**Wealth creation is an engineering discipline, not a gamble.** However, automated trading still carries significant financial risk. Olympus is designed to minimize regret, but it cannot eliminate the inherent risks of the financial markets. Use responsibly.

[image1]: <data:image/png;base64,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>