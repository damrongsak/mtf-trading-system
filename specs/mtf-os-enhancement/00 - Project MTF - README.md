# **Project MTF: The Trading Operating System (Trading OS)**

**Project MTF** is a professional-grade Multi-Agent Decision Intelligence System designed for institutional-level trading execution. Unlike traditional trading bots, MTF functions as an **Operating System** where strategies are modular plugins, and AI serves as a reasoning advisor, decoupled from the core execution and risk kernel.

## **👁️ The Vision: "The MTF Way"**

* **Decoupling Reality from Decision:** Separation of Market Reality (Layers 1-3) from Strategy Logic.  
* **Risk as Kernel:** Layer 4 (Risk) acts as the system kernel with absolute authority to override any trade.  
* **AI as Intelligence Advisor:** LLMs perform reasoning and context synthesis without direct execution rights.  
* **Deterministic & Auditable:** Every decision is stateless, replayable, and fully transparent.

## **⚙️ Core Architecture: Multi-Agent Framework**

MTF is structured around a 5-layer autonomous agent architecture:

| Agent / Layer | Technology Stack | Responsibility |
| :---- | :---- | :---- |
| **1\. Probability Agent** | Monte Carlo, Block Bootstrap | Define statistical price boundaries (p10/p50/p90). |
| **2\. Structure Agent** | ATR-Grid, OI Density Nodes | Identify structural market edges and "gravity" zones. |
| **3\. Execution Context** | SMC (CHoCH, OB, FVG) | Filter trade quality based on market structure shifts. |
| **4\. Risk & Guardrail** | Dynamic Sizing, Kill Switch | **Kernel Layer:** Enforce hard risk constraints and safety. |
| **5\. Reasoning Agent** | Gemini 1.5 Pro, RAG | Synthesize market narrative and provide rationales. |

## **🧠 Intelligence Engine: RAG as Context Retrieval**

In MTF, RAG is not just for document Q\&A; it is a **Context Retrieval Engine** that powers decision intelligence:

* **Retrieve:** Fetch historical trade logs, similar market regimes, and strategy playbooks from **Qdrant**.  
* **Augment:** Enrich LLM prompts with structured data from Layers 1-3 to build a grounded hypothesis.  
* **Generate:** Produce auditable trade rationales and explainable risk reports.

## **📊 Evaluation: The Gold Standard**

MTF implements a rigorous evaluation pipeline to ensure production-readiness:

1. **Offline Evaluation:** Extensive backtesting using vectorbt for Sharpe Ratio and Tail Risk analysis.  
2. **Online Evaluation:** Real-time comparison between Live and Paper trading performance.  
3. **LLM Evaluation:** Monitoring for **Decision Consistency** and **Hallucination Rates** (e.g., cross-referencing AI rationales with structural data).  
4. **Regression Testing:** Ensuring that the same market state always leads to the same deterministic decision.

## **🏗️ Technical Stack**

* **Language:** Python 3.13 (Core), Next.js 15 / React 19 (Frontend)  
* **Backend:** FastAPI (Microservices), Celery (Async Tasks), uv (Package Management)  
* **Databases:** PostgreSQL 15 (Structured/Embeddings), Qdrant (Vector Store)  
* **AI/LLM:** Gemini 1.5 Pro via Google Cloud Vertex AI  
* **Infrastructure:** Dockerized Microservices, Nginx Reverse Proxy  
* **Cloud:** Google Cloud Platform (Cloud Run, Cloud SQL, Secret Manager)

## **📂 Project Structure**

mtf-trading-os/  
│  
├─ services/  
│   ├─ api-gateway/        \# Central routing & authentication  
│   ├─ strategy-core/      \# Strategy Plugin Engine & Backtesting  
│   ├─ ai-analyst/         \# Reasoning Agent & RAG Service  
│   ├─ execution/          \# OANDA Integration & Risk Kernel  
│   └─ data-pipeline/      \# Multi-timeframe data ingestion  
│  
├─ frontend/               \# Decision Intelligence Dashboard  
├─ specs/                  \# SDD: Specification Driven Development  
└─ docker-compose.yml      \# Orchestration for local development

## **🧭 Roadmap & Implementation**

Following the **Spec-Driven Development (SDD)** flow:

1. **Define Contracts:** Finalize API and Data models in /specs.  
2. **Scaffold Engine:** Generate service stubs from specifications.  
3. **Agent Integration:** Connect Reasoning Agents with RAG and Market Data.  
4. **Hardening:** Implement the Risk Guardrail Kernel.  
5. **Audit Loop:** Enable full traceability for every tool call and decision.

## **📜 License**

This project is licensed under the **Apache License 2.0**. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

## **⚖️ Disclaimer**

Project MTF is an advanced decision support system for educational and research purposes. All trading involves significant risk. The authors assume no responsibility for financial outcomes. **Survival is Mandatory; Profits are Optional.**