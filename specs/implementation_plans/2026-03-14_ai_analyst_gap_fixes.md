# Implementation Plan - Fit Gaps for Olympus AI Analyst (Strategic Improvement)

**Date:** 2026-03-14
**Status:** PLANNED
**Target:** AI Analyst Reliability & Memory

## 1. Overview
This plan addresses critical gaps identified in the "Olympus AI Analyst - Strategic Analysis" report (2026-03-14). The goal is to improve system resilience (LLM Fallback), tool execution reliability (Parameter Validation), and cognitive capabilities (Memory & Reasoning).

## 2. Proposed Changes

### 2.1. LLM Resilience & Fallback
- **File:** `services/ai-analyst/app/services/gemini.py`
- **Change:** Integrate `OpenRouterClient` as a Tier 3 fallback in `GeminiClient.generate_content`.
- **Logic:** If Gemini returns a 503 (Service Unavailable) or 429 (Quota) and all Gemini fallbacks are exhausted, route the request to OpenRouter (Claude-3.5-Sonnet).
- **Timeout:** Enforce a strict 30s timeout on all LLM API calls.

### 2.2. Tool Validation Fixes
- **File:** `services/ai-analyst/app/tools/smc.py`
- **Change:** Update `SMCInput` Pydantic model.
- **Fix:** Make `symbol` field optional with a default of `"XAUUSD"`. Ensure the `run_tool` logic handles missing keys gracefully.

### 2.3. Conversation Continuity (Memory)
- **File:** `services/ai-analyst/app/agents/strategy_advisor.py`
- **Change:** Update `node_query_optimizer` and `node_generate`.
- **Fix:** Increase the number of messages passed for context from the last 6 (3 turns) to the last 10 (5 turns).

### 2.4. Tool Reliability (Self-Correction)
- **File:** `services/ai-analyst/app/agents/strategy_advisor.py`
- **Change:** Update `node_execute_tools`.
- **Feature:** Implement a single-retry mechanism for tools that return an error string. If a tool fails, wait 1s and retry once before reporting failure to the agent.

### 2.5. Response Quality Evaluation
- **File:** `services/ai-analyst/app/agents/strategy_advisor.py`
- **Change:** Update `node_evaluator`.
- **Feature:** Enhance the prompt to specifically score the response quality (0-100) and require a score > 80 for "satisfactory" status.

## 3. Verification Roadmap

### Phase 1: Unit & Integration
1. **Tool Check:** `python services/ai-analyst/check_imports.py`
2. **Fallback Simulation:** Mock `google.genai.Client` to raise a 503 and verify OpenRouter execution.
3. **Validation Test:** Call `smc_technical_analysis` via the test endpoint without a symbol.

### Phase 2: E2E Flow
1. Verify multi-turn dialogue maintains context (e.g., "Analyze Gold", then "What was the price I just mentioned?").
2. Trigger a transient tool failure (mocked) and verify the retry in logs.

## 4. References
- [Strategic Analysis Report](file:///Ubuntu-24.04/home/dan/workspace/mtf-trading-system/services/ai-analyst/AI_ANALYST_ANALYSIS.md)
- [AI Agent Specification](file:///Ubuntu-24.04/home/dan/workspace/mtf-trading-system/specs/06_ai_agent.md)
