---
name: ai-agent-guardrails
description: Best practices and guardrails for implementing AI agents to prevent infinite loops, token limit explosion, and state bleeding in LangGraph.
---

# AI Agent Guardrails

This skill outlines the critical design patterns and defensive programming techniques required when building or modifying AI Agents (especially using LangGraph and LLMs like Gemini) within this system. Follow these instructions to ensure stability, cost-efficiency, and correct end-to-end behavior.

## 1. Context & Memory Management (Preventing Token Explosion)

LLMs have absolute token limits (e.g., TPM quotas or context window). Do not allow agent memory or scratchpads to grow infinitely.

*   **Hard Truncation**: When passing historical context (like a `scratchpad` of previous tool outputs or `retrieved_docs`) into an LLM prompt, **always enforce a hard character limit**.
    *   *Example:* `scratchpad = raw_scratchpad[-20000:]` or `docs = raw_docs[:10000]`
*   **Summarizer Replacement**: If using a summarizer node to condense past actions, ensure it **replaces** the history rather than appending to it. Do not use accumulators (like `operator.add`) for summarized states if the summary itself contains the whole history.
*   **Token Counting Middleware**: Before dispatching a heavy CoT (Chain of Thought) payload or a generation prompt, assess the string length or token count. If it approaches the API quota, trim it aggressively or raise an internal exception to halt the loop safely.

## 2. Agent Guardrails (Preventing Infinite Loops & Hallucinations)

Agents can get stuck in loops, repeatedly calling the same tools or hallucinating tool calls when data is already sufficient.

*   **Explicit Stopping Conditions**: System prompts (especially Tool Routers) MUST contain aggressive stopping conditions.
    *   *Directive Example:* "If the necessary data to answer the user's request is already present in the **Recent Tool Outputs**, you MUST NOT call any more tools. Return an empty `tool_calls` array."
*   **De-duplication**: In the tool selection node, always hash or compare the requested tool name and arguments against previous calls in the same session. If an identical call was just made, drop it to prevent looping.
*   **Max Iterations**: Always set a hard limit on the number of graph iterations (e.g., `recursion_limit` in LangGraph config or an explicit `tool_loop_count` state variable). If the agent hits this limit, force a graceful degradation or fallback response.

## 3. State Isolation (Preventing Session Bleeding)

When agents operate in a stateless environment (e.g., REST API calls) but use stateful orchestrators (like LangGraph Checkpointers), state can bleed between unconnected requests.

*   **Ephemeral Thread IDs**: For stateless requests or tests, **never** default to a static identifier like `user_id` for the checkpointer's `thread_id`. If omitted by the client, generate a fresh `uuid4()` on the backend.
    *   *Why:* Defaulting to `user_id` causes all stateless calls for that user to share the same history, causing the LLM to trigger false stopping conditions based on previous queries, or blowing up the prompt size.
*   **Stateless Test Environments**: When writing automated verification tests (Pytest) or E2E scripts, use an ephemeral memory saver (e.g., `MemorySaver()` from LangGraph) rather than a persistent database/Redis saver, to ensure tests do not pollute the main session store.

---
**When to Use this Skill:** Apply these checks during code reviews of `ai-analyst` components, when adding new tools, tuning prompts, or debugging agent timeouts/crashes.
