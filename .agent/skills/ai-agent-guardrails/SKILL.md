---
name: ai-agent-guardrails
description: Best practices and guardrails for implementing AI agents and resilient tools to prevent infinite loops, state bleeding, and tool execution failures.
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

## 4. Institutional Tool Standards (Resilience Layer)

To ensure institutional stability, all tools in this project MUST inherit from our resilient base class rather than standard LangChain classes. Failure to do so bypasses retries, circuit breakers, and concurrency controls.

*   **Inheritance**: ALWAYS inherit from `app.core.base_tool.BaseTool`.
    *   *Bad:* `from langchain_core.tools import BaseTool`
    *   *Good:* `from app.core.base_tool import BaseTool`
*   **Method Implementation**: Implementation logic MUST live in `async def run_tool()`.
    *   **NEVER** implement `_run()`, `run()`, or `_arun()`. These are handled by the BaseTool's resilience layer.
*   **Input Normalization**: `run_tool` receives a single `input_data` argument which can be a `dict` (for structured tools) or a `str` (for simple tools).
    *   *Pattern:*
        ```python
        async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
            # 1. Normalize
            symbol = "XAUUSD"
            if isinstance(input_data, dict):
                symbol = input_data.get("symbol", symbol)
            elif isinstance(input_data, str):
                symbol = input_data
            
            # 2. Execute with meta (auth_token/request_id is passed in kwargs)
            ...
        ```
*   **Metadata**: `auth_token` and `request_id` are injected by the orchestrator into the tool execution context. Always include them in your `run_tool` signature if network calls are required.
    
## 5. Service Decoupling & Communication Patterns (Anti-Deadlock)

To prevent reentrancy deadlocks (circular dependencies) and high-coupling, all tools and service logic MUST follow these institutional patterns:

*   **🚫 NO REENTRANT GATEWAY CALLS**: AI Tools MUST NOT call the `api-gateway` from within another internal service to fetch data.
*   **Direct Service Calls**: If Service A needs data from Service B, it should call B's internal endpoint directly OR use a shared client.
*   **ECST (Event-Carried State Transfer)**: For frequently accessed data (like News, Symbol Metadata), services should subscribe to events and cache state locally in Redis/Memory for O(1) reads.
*   **Async RPC**: Use Redis Queues for high-latency or risky operations instead of blocking HTTP requests.
*   **Communication Choice Matrix**:
    *   *Read-heavy / Static*: Use **ECST** (Local Cache).
    *   *Complex / Batch Read*: Use **CQRS Read Model** (Qdrant/JSONB).
    *   *Simple Response*: Use **API Composition** (Gateway aggregates; services stay isolated).
    *   *Write/Heavy Logic*: Use **Async RPC** (Message Broker).

---
**When to Use this Skill:** Apply these checks during code reviews of `ai-analyst` components, when adding new tools, tuning prompts, or debugging agent timeouts/crashes.
