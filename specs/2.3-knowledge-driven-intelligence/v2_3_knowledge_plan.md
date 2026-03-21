# Implementation Plan: Minor Enhancement (v2.3) - Knowledge-Driven Intelligence

## Goal
Elevate the system from "Data-Flow Hardened" to "Knowledge-Integrated" by bridging the gap between the Knowledge Graph (FalkorDB) and the Execution/Strategy cores.

## User Review Required
> [!IMPORTANT]
> This version introduces **Intelligent Signal Filtering**. Signals that directly contradict "War Premium" or "High-Impact Geopolitics" in the Knowledge Graph may be rejected or reduced in size automatically.

## Proposed Changes

### 1. GraphRAG Integration Layer (`services/ai-analyst`)
- **Knowledge Retrieval API**: Add `/query/context` endpoint to `ai-analyst` that accepts an asset (e.g., XAUUSD) and returns a semantic summary from FalkorDB.
- **Node Merging Worker**: Implement a background task in `knowledge-ingestor` to merge synonymous nodes (e.g., "Gold" -> "XAUUSD") using LLM-based entity resolution.

### 2. Semantic Signal Validation (`services/strategy-core`)
- **Contextual Filter**: Update the strategy engine to call the `AIAnalystClient` for a "Market Context" check before emitting a signal.
- **Contradiction Detection**: If a "Long Gold" signal is generated while the Knowledge Graph identifies a "Liquidity Sweep" at a major resistance level, the signal's `confidence` score will be adjusted.

### 3. Knowledge-Driven Risk Scoring (`services/execution`)
- **Dynamic Leverage**: Modify the Risk Engine to incorporate a `knowledge_score` (0.5x to 1.5x) into position sizing. 
- **Sentiment Weighting**: Use the `WebIntelligence` nodes in FalkorDB to adjust "Minimax Regret" parameters based on live sentiment.

### 4. Spec Updates (`specs/`)
- **03_data_model.yaml**: Add `knowledge_context` JSONB field to `Trade` and `Signal` models.
- **08_execution_rules.md**: Define "Institutional Knowledge Override" rules.

## Verification Plan
### Automated Tests
- **GraphRAG Test**: Mock a "War Premium" node in FalkorDB and verify `ai-analyst` returns it as part of the context for XAUUSD.
- **Signal Integrity**: Verify a signal's `risk_multiplier` changes based on the presence of "Counter-Trend" concepts in the graph.

### Manual Verification
- Run a "Long Gold" test trade while a "Bearish Divergence" concept is manually added to the graph.
- Confirm the Execution Service logs show "Risk adjusted due to Knowledge Context".
