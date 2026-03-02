from typing import TypedDict, Annotated, List, Union
import operator
import json
import logging
import asyncio
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService
from app.services.semantic_cache import SemanticCache
from app.core.config import settings
from app.core.schemas import (
    QueryOptimization,
    PlanDecomposition,
    SystemToolCall,
    SystemToolSelection,
    EvaluationResult
)


from app.core.prompts import (
    SYSTEM_PERSONA, 
    RETRIEVAL_SYSTEM_PROMPT, 
    REASONING_PROMPT_TEMPLATE,
    TOOL_ROUTER_SYSTEM_PROMPT
)
from app.core.base_tool import BaseTool
from app.core.tools import ToolRegistry

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """
    The state of the Strategy Advisor Agent.
    """
    # Messages
    input_text: str
    user_id: str
    auth_token: str # Derived from API call
    messages: Annotated[List[dict], operator.add] # Persistent Chat History
    
    # Internal State
    optimized_query: str
    intent: str # 'chat', 'strategy_design', 'market_analysis', 'research', 'tool_use'
    plan_steps: List[str]
    tool_calls: List[dict] # Selected tools to run
    
    # Context
    retrieved_docs: List[str]
    user_facts: List[str]
    market_context: str
    strategy_code: str
    
    # Outputs
    reasoning_trace: List[str]
    final_response: str
    thoughts: str # Captured from Thinking models
    
    # Safety / HITL
    pending_tool_call: dict # Tool call waiting for confirmation
    
    # Scratchpad for tool outputs
    scratchpad: List[str]
    
    # Agentic RAG / Iterative Refinement
    iteration_count: int
    tool_loop_count: int # Execution turns count
    evaluation_feedback: str
    is_satisfactory: bool

class StrategyAdvisorAgent:
    def __init__(self, 
                 rag_service: RAGService, 
                 gemini_client: GeminiClient, 
                 checkpointer: BaseCheckpointSaver = None,
                 memory_service: MemoryService = None):
        
        self.rag = rag_service
        self.gemini = gemini_client
        self.memory = memory_service
        self.cache = SemanticCache(gemini_client)
        self.checkpointer = checkpointer
        
        # Initialize Tools
        self.tool_registry = ToolRegistry(rag_service)
        
        # Build the Graph
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # 1. Add Nodes
        workflow.add_node("query_optimizer", self.node_query_optimizer)
        workflow.add_node("router", self.node_router)
        workflow.add_node("decompose", self.node_decompose)
        workflow.add_node("retrieve_knowledge", self.node_retrieve)
        workflow.add_node("reasoning", self.node_reason)
        workflow.add_node("generate", self.node_generate)
        workflow.add_node("evaluator", self.node_evaluator)

        workflow.add_node("memory_write", self.node_memory_write)
        workflow.add_node("check_cache", self.node_check_cache)
        
        # New Nodes for Advanced Features
        workflow.add_node("synthesize", self.node_synthesize) # Deep Research
        workflow.add_node("tool_selection", self.node_tool_selection) 
        workflow.add_node("execute_tools", self.node_execute_tools)
        workflow.add_node("summarizer", self.node_scratchpad_summarizer)

        # Consolidated Nodes
        workflow.add_node("market_scan", self.node_market_scan)
        workflow.add_node("generate_briefing", self.node_generate_briefing)

        # 2. Add Edges
        workflow.set_entry_point("query_optimizer")
        
        workflow.add_edge("query_optimizer", "check_cache")

        workflow.add_conditional_edges(
            "check_cache",
            lambda x: "cache_hit" if x.get("from_cache") else "miss",
            {
                "cache_hit": END,
                "miss": "router"
            }
        )
        
        # Enhanced Router Logic
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "direct": "generate",
                "complex": "decompose",
                "research": "retrieve_knowledge", # Research goes to RAG -> Synthesize
                "tool_use": "tool_selection",
                "confirmation_check": "tool_selection", # Route pending confirmations here
                "market_scan": "market_scan",
                "generate_briefing": "generate_briefing"
            }
        )
        
        workflow.add_edge("decompose", "retrieve_knowledge")
        
        # Retrieve Knowledge Logic
        workflow.add_conditional_edges(
            "retrieve_knowledge",
            lambda x: "synthesize" if x.get("intent") == "RESEARCH" else "reasoning",
            {
                "synthesize": "synthesize",
                "reasoning": "reasoning"
            }
        )

        workflow.add_conditional_edges(
            "tool_selection",
            self._route_selection_output,
            {
                "execute": "execute_tools",
                "done": "generate"
            }
        )
        
        workflow.add_edge("execute_tools", "summarizer")
        workflow.add_edge("summarizer", "tool_selection")
        
        workflow.add_edge("reasoning", "tool_selection") # Pass plan to tool selector
        workflow.add_edge("synthesize", "memory_write") # Research ends here usually

        # Edges for Consolidated Nodes
        workflow.add_edge("market_scan", "generate")
        workflow.add_edge("generate_briefing", "generate")
        
        workflow.add_edge("generate", "evaluator")
        
        workflow.add_conditional_edges(
            "evaluator",
            self._route_evaluation,
            {
                "satisfactory": "memory_write",
                "refine": "decompose",
                "max_iterations": "memory_write"
            }
        )
        
        workflow.add_edge("memory_write", END)

        # 3. Compile
        return workflow.compile(checkpointer=self.checkpointer)

    # --- NODE IMPLEMENTATIONS ---

    async def node_query_optimizer(self, state: AgentState):
        """
        Uses Gemini Flash to optimize the query and classify intent.
        Includes chat history for context-aware queries.
        """
        query = state["input_text"]
        logger.info(f"Optimizing query: {query}")
        
        # Format recent history for context
        history = state.get("messages", [])
        history_str = "No recent history."
        if history:
             # Only use the last 6 messages (3 turns) to prevent context bloat
             recent = history[-6:]
             history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])
             
        prompt = f"""
        You are a Query Optimizer for a Hedge Fund AI (MTF Olympus).
        Your goal is to rewrite the user's raw query into a clear, unambiguous Request and classify its INTENT.
        
        Raw Query: "{query}"
        
        **Instructions:**
        1. **Translate to English**: If the raw query is not in English, translate it to clear technical English.
        2. **Infer Symbol**: If no symbol is mentioned, default to "XAUUSD" (Gold) as this is our primary asset.
        3. **Normalize Timeframe**: Standardize timeframes (e.g., "5min" -> "M5", "1h" -> "H1").
        4. **Be Technical and CONCISE**: The optimized query should be a **vector search query**. REMOVE conversational debris like "Search the library for", "Give me an answer on", "What is", or "Can you find". 
        - Bad: "Search the quant library for the formula for Kelly Criterion."
        - Good: "Kelly Criterion mathematical formula and application"
        - Bad: "What is my balance?"
        - Good: "Account balance and equity status"
        5. **Include Context**: Include the symbol and timeframe in the optimized query if relevant.
        
        **Intents:**
        - **TOOL_USE**: User asks to PERFORM an action using a system tool. This includes:
            - Getting account data (balance, equity, positions, margin)
            - **Generating a trading plan or buy/sell setup** (uses the `generate_trading_plan` tool)
            - Sending notifications or alerts to Telegram
            - Placing orders, checking risk
        - **MARKET_ANALYSIS**: User asks for a market outlook, price narrative, institutional analysis, or general commentary — WITHOUT requesting a structured plan output.
        - **RESEARCH**: User asks a complex quantitative "How to" question about the system, requiring documentation retrieval.
        - **STRATEGY_DESIGN**: User wants to CREATE, modify, or optimize a trading strategy or code.
        - **MARKET_REPORT**: User asks for a broad overview of the market (Market Observer mode).
        - **DAILY_BRIEFING**: User asks for their daily trading checklist or journal summary.
        - **CHAT**: General conversation or simple questions not requiring real-time data or tools.
        
        **Previous Chat History for Context:**
        {history_str}
        
        **CRITICAL**: 
        1. If the user asks for balance, equity, positions, margin, or trade actions, ALWAYS classify as **TOOL_USE**.
        2. If the user says "generate a trading plan", "give me a plan", "buy/sell setup", or "what should I trade", ALWAYS classify as **TOOL_USE** (not MARKET_ANALYSIS).
        3. If the user says "send to telegram", "notify me", "alert me", or "send it", ALWAYS classify as **TOOL_USE**.
        4. If the user asks for a trading plan AND wants it sent to Telegram, keep it **TOOL_USE** — the agent will call both tools in sequence.
        5. Only use **MARKET_ANALYSIS** for open-ended commentary or institutional analysis WITHOUT a specific plan output requested.
        
        **Output JSON only:**
        {{
            "optimized_query": "...",
            "intent": "..."
        }}
        """
        
        try:
            # Tier 1 fallback logic
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_lite_model_id, settings.gemini.flash_model_id, "gemini-2.0-flash-lite"], 
                contents=[prompt],
                response_schema=QueryOptimization
            )
            
            # The SDK will return a parsed object if response_schema is provided
            # and our wrapper returns response.text (which should be the JSON string)
            text = response.get("text", "")
            data = QueryOptimization.model_validate_json(text)
            
            logger.info(f"Optimization Result - Intent: {data.intent}, Query: {data.optimized_query}")
            return {
                "optimized_query": data.optimized_query,
                "intent": data.intent
            }
        except Exception as e:
            logger.error(f"Optimizer failed: {e}")
            return {"optimized_query": query, "intent": "CHAT"}

    async def node_check_cache(self, state: AgentState):
        """
        Checks semantic cache for existing valid responses.
        Skipped for real-time/tool-use intents.
        """
        query = state["optimized_query"]
        intent = state.get("intent", "CHAT")
        
        # Only cache RESEARCH and STRATEGY_DESIGN 
        if intent in ["RESEARCH", "STRATEGY_DESIGN"]:
            if self.cache:
                cached_response = await self.cache.check(query)
                if cached_response:
                    logger.info(f"✨ Semantic Cache HIT for: {query}")
                    return {
                        "final_response": "✨ (Cached) " + cached_response, 
                        "from_cache": True,
                        "is_satisfactory": True
                    }
        
        return {"from_cache": False}

    async def node_router(self, state: AgentState):
        """
        Passthrough node - routing logic handles the split.
        In a more complex graph, this could do more classification.
        """
        return {} # State update if needed

    def _route_decision(self, state: AgentState):
        """
        Conditional Logic: Routes based on Intent.
        """
        # Prioritize Pending Confirmation
        if state.get("pending_tool_call"):
            return "confirmation_check"
            
        intent = state.get("intent", "CHAT")
        query_text = state.get("input_text", "").lower()
        
        if intent == "TOOL_USE":
            # Direct Tool Request bypasses reasoning (e.g., "what is my balance")
            # If it's a simple command, go straight to tool selection to save tokens
            return "tool_use"
        elif intent == "RESEARCH":
            return "research"
        elif intent in ["STRATEGY_DESIGN", "MARKET_ANALYSIS"]:
            return "complex"
        elif intent == "MARKET_REPORT":
            return "market_scan"
        elif intent == "DAILY_BRIEFING":
            return "generate_briefing"
        
        return "direct"

    def _route_evaluation(self, state: AgentState):
        """
        Routes based on evaluation result.
        """
        if state.get("is_satisfactory"):
            return "satisfactory"
        
        if state.get("iteration_count", 0) >= 3:
            logger.warning("Max Agentic RAG iterations reached.")
            return "max_iterations"
            
        return "refine"

    def _route_selection_output(self, state: AgentState):
        """
        Routes based on whether tools were selected or we are done.
        """
        # If tools were selected, go to execution
        if state.get("tool_calls"):
            # Limit loops using turn-based count
            loop_count = state.get("tool_loop_count", 0)
            intent = state.get("intent", "CHAT")
            
            # Dynamic Turn Limits: 
            # - RESEARCH queries get 10 turns
            # - Standard queries get 5 turns to minimize latency
            max_turns = 10 if intent == "RESEARCH" else 5
            
            logger.debug(f"Loop Check: turn={loop_count}, intent={intent}, max={max_turns}, tools_this_turn={len(state['tool_calls'])}")
            
            if loop_count >= max_turns:
                logger.warning(f"Max tool execution turns ({max_turns}) reached for intent {intent}. Forcing generation.")
                return "done"
            return "execute"
            
        # No tools selected -> Move to final response generation
        return "done"

    async def node_decompose(self, state: AgentState):
        """
        Breaks down the optimized query into reasoning steps.
        """
        query = state["optimized_query"]
        prompt = f"""
        Decompose this quantitative request into 3-5 logical reasoning steps.
        Request: "{query}"
        
        Output valid JSON List of strings:
        ["Step 1...", "Step 2..."]
        """
        try:
            # Tier 1: High-Volume / Reductive
            # Tier 1 fallback logic
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_model_id, settings.gemini.model_id, "gemini-2.0-flash"],
                contents=[prompt],
                response_schema=PlanDecomposition
            )
            text = response.get("text", "")
            data = PlanDecomposition.model_validate_json(text)
            return {"plan_steps": data.plan_steps}
        except:
             return {"plan_steps": ["Analyze Request", "Retrieve Data", "Formulate Answer"]}

    async def node_retrieve(self, state: AgentState):
        """
        Contextual Retrieval from Qdrant and Memory.
        Parallelized for speed and enhanced with explicit logging.
        """
        query = state["optimized_query"]
        user_id = state["user_id"]
        intent = str(state.get("intent", "CHAT")).upper().strip()
        
        # dynamic top_k based on intent
        top_k = 10 if intent == "RESEARCH" else 5
        logger.info(f"🔍 Retrieval started | Intent: {intent} | Query: '{query}' | Target Results: {top_k}")

        # Define tasks for parallel execution
        tasks = []
        
        # 1. User Context (Long Term Memory)
        if self.memory:
            tasks.append(self.memory.get_user_context(user_id, query))
        else:
            tasks.append(asyncio.sleep(0, result="No memory service available."))

        # 2. System Docs (Specs/Guides)
        tasks.append(self.rag.search_documentation(query, limit=top_k))

        # 3. Quant Library (Financial Knowledge) - Only for RESEARCH or complex strategy design
        if intent in ["RESEARCH", "STRATEGY_DESIGN"]:
            tasks.append(self.rag.search_library(query, limit=top_k + 2))
        else:
            # Return empty list to satisfy the result unpacking
            async def get_empty(): return []
            tasks.append(get_empty())

        # 4. Strategies (Code)
        tasks.append(self.rag.search_similar_strategies(query, user_id, limit=top_k))

        # Execute all retrieval tasks in parallel
        results = await asyncio.gather(*tasks)
        
        user_facts_str = results[0]
        system_docs = results[1]
        library_docs = results[2]
        strategies = results[3]

        user_facts = [user_facts_str] if user_facts_str and "No specific user preferences" not in user_facts_str else []
        
        # Format doc texts with explicit sources
        doc_texts = [f"[Source: {d['filename']}]\n{d['content']}" for d in system_docs]
        lib_texts = [f"[Source: Quant Library - {d['filename']}]\n{d['content']}" for d in library_docs]
        strat_texts = [f"[Strategy: {s.get('name', 'Unnamed')}]\n{s['code']}" for s in strategies]

        logger.info(f"✅ Retrieval complete | UserFacts: {len(user_facts)} | SystemDocs: {len(doc_texts)} | LibraryDocs: {len(lib_texts)} | Strategies: {len(strat_texts)}")

        # 5. Inject Tool Context (Dynamic Capabilities)
        tool_info = self.tool_registry.get_tool_descriptions()
        tool_ctx = f"**Available System Tools:**\n{tool_info}"
        
        # 6. Agentic RAG: Use evaluation feedback to refine search if present
        refinement_ctx = []
        if state.get("evaluation_feedback"):
             refinement_ctx.append(f"**Previous Evaluation Feedback (Reason to refine search):**\n{state['evaluation_feedback']}")
        
        # Merge and Prune
        max_chunks = 20 if intent == "RESEARCH" else 12
        existing_docs = state.get("retrieved_docs", []) or []
        
        # Priority: Quant Library results at the VERY TOP for Research intents
        # Then system docs, strategies, tools.
        if intent == "RESEARCH":
            combined_docs = lib_texts + doc_texts + strat_texts + refinement_ctx + [tool_ctx] + existing_docs
        else:
            combined_docs = existing_docs + [tool_ctx] + refinement_ctx + doc_texts + lib_texts + strat_texts
        
        # Unique and latest N
        pruned_docs = list(dict.fromkeys(combined_docs))[:max_chunks]
        
        return {
            "user_facts": user_facts,
            "retrieved_docs": pruned_docs
        }

    async def node_reason(self, state: AgentState):
        """
        CoT Reasoning Step: Synthesize ALL retrieved info.
        """
        steps = state.get("plan_steps", [])
        context = "\n\n".join(state.get("retrieved_docs", []))
        user_facts = "\n".join(state.get("user_facts", []))
        
        trace = []
        # We simulate a "Thinking" process by prompting the model to reason about the data
        from datetime import datetime
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        prompt = REASONING_PROMPT_TEMPLATE.format(
            context=context,
            user_facts=user_facts,
            query=f"{state['optimized_query']}\n(Current Date: {current_date})"
        )
        
        try:
            # High-fidelity Reasoning (Pro models only)
            response = await self.gemini.generate_content(
                model=[settings.gemini.model_id, "gemini-2.5-pro", "gemini-3.1-pro-preview"],
                contents=[prompt]
            )
            new_trace_item = response.get("text", "")
        except:
            new_trace_item = "Reasoning failed."
        
        # Prune reasoning_trace manually (keep latest 5)
        existing_trace = state.get("reasoning_trace", []) or []
        return {"reasoning_trace": (existing_trace + [new_trace_item])[-5:]}

    async def node_tool_selection(self, state: AgentState):
        """
        Selects the best tool for the job. Handles HITL Confirmation.
        """
        # 1. Handle Pending Confirmation
        pending = state.get("pending_tool_call")
        if pending:
            user_response = state["input_text"].strip().upper()
            logger.info(f"Processing Confirmation: {user_response}")
            
            # Simple keyword matching for now
            if user_response in ["YES", "CONFIRM", "EXECUTE", "OK", "SURE", "Y"]:
                # Confirmed -> Move to execution
                return {"tool_calls": [pending], "pending_tool_call": None}
            else:
                # Denied -> Cancel
                return {"pending_tool_call": None, "scratchpad": ["Action cancelled by user."]}

        # 2. Normal Selection
        query = state["optimized_query"]
        tool_descriptions = self.tool_registry.get_tool_descriptions()
        
        # Inject Current Date for relative time reasoning
        from datetime import datetime
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Include Reasoning Trace if available (The Plan)
        reasoning_context = ""
        if state.get("reasoning_trace"):
             reasoning_context = f"\n\n**Agent Plan (Reasoning Trace):**\n{state['reasoning_trace'][0]}"

        # Include Previous Tool Results (Scratchpad)
        tool_results = ""
        if state.get("scratchpad"):
            formatted_outputs = []
            total_chars = 0
            # Hard cap: only last 6000 chars total from the MOST RECENT entries
            # Use raw scratchpad entries NOT summarized-accumulated ones, to avoid 1M+ prompts
            MAX_CHARS = 6000
            for output in reversed(state["scratchpad"]):
                # Skip internal summary markers that contain all previous turns
                if "--- CONDENSED SUMMARY OF PREVIOUS STEPS ---" in str(output):
                    # Only include the summary itself, stripped of marker, at most 3000 chars
                    clean = str(output).replace("--- CONDENSED SUMMARY OF PREVIOUS STEPS ---", "").strip()[:3000]
                else:
                    clean = str(output)[:1500]
                if total_chars + len(clean) > MAX_CHARS:
                    break
                formatted_outputs.append(f"--- Tool Output ---\n{clean}\n")
                total_chars += len(clean)
            
            tool_results = f"\n\n**Recent Tool Outputs:**\n" + "\n".join(reversed(formatted_outputs))

        prompt = TOOL_ROUTER_SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            query=f"{query}\n(Current Date: {current_date}){reasoning_context}{tool_results}"
        )
        
        logger.info(f"Tool Selection - Query: {query} | Context/Trace: {len(reasoning_context)} chars | Scratchpad: {len(tool_results)} chars")
        # 2. Reasoning Loop Hard Cap
        loop_count = state.get("tool_loop_count", 0)
        if loop_count >= 7:
            logger.warning(f"Reasoning Loop Hard Cap reached ({loop_count}). Forcing generation.")
            return {"intent": "CHAT", "tool_calls": []} # Transition to generate
            
        try:
            # Tier 2 (3-Model Fallback)
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_model_id, settings.gemini.model_id, "gemini-2.5-flash"],
                contents=[prompt],
                response_schema=SystemToolSelection
            )
            
            text = response.get("text", "")
            # Clean up potential markdown formatting if not using schema
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            decision = SystemToolSelection.model_validate_json(text)

            logger.info(f"Selected {len(decision.tool_calls)} tools: {[t.tool_name for t in decision.tool_calls]}")
            
            if not decision.tool_calls and not decision.direct_answer:
                return {"tool_calls": []}

            # Populate scratchpad if direct answer exists
            res_ext = {}
            if decision.direct_answer:
                res_ext["scratchpad"] = [f"System Observation: {decision.direct_answer}"]

            # Helper for executing tools (mapping Pydantic to list of dicts)
            raw_tool_calls = [t.model_dump() for t in decision.tool_calls]
            
            # Enforce uniqueness programmatically to prevent redundant execution
            seen_tools = set()
            tool_calls = []
            for tc in raw_tool_calls:
                name = tc.get("tool_name")
                if name not in seen_tools:
                    seen_tools.add(name)
                    tool_calls.append(tc)
                else:
                    logger.warning(f"Discarding redundant tool call: {name}")
            
            return {**res_ext, "tool_calls": tool_calls}
            
        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            return {}

    async def node_execute_tools(self, state: AgentState):
        """
        Executes selected tools and adds output to scratchpad.
        Optimized: Runs tools in parallel using asyncio.gather.
        """
        calls = state.get("tool_calls", [])
        outputs = []
        
        from app.utils.middleware import get_request_id
        from app.utils.token_monitor import TokenMonitor
        request_id = get_request_id()
        auth_token = state.get("auth_token")
        
        # Check for context saturation to trigger "Slim Mode"
        scratchpad_text = "\n".join(state.get("scratchpad", []))
        is_saturated = TokenMonitor.is_saturated(scratchpad_text)

        async def exec_tool(call, current_auth_token, current_request_id):
            tool_name = call.get("tool_name")
            tool_input = call.get("tool_input")
            
            # Inject auth_token/user_id/request_id into input context
            if isinstance(tool_input, dict):
                if current_auth_token:
                    if "auth_token" not in tool_input or not tool_input["auth_token"]:
                        tool_input["auth_token"] = current_auth_token
                    if "user_id" not in tool_input or not tool_input["user_id"]:
                        tool_input["user_id"] = state.get("user_id")
                
                if current_request_id and ("request_id" not in tool_input or not tool_input["request_id"]):
                    tool_input["request_id"] = current_request_id
                
                # Token-Aware Routing: Force slim mode if saturated
                if is_saturated and "slim" not in tool_input:
                    tool_input["slim"] = True

            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                try:
                    # Handle both local BaseTool and Langchain BaseTool
                    if hasattr(tool, "run") and not hasattr(tool, "_arun"):
                        # Local BaseTool
                        result = await tool.run_resilient(tool_input, auth_token=current_auth_token, request_id=current_request_id)
                    else:
                        # Langchain Tool
                        if isinstance(tool_input, dict):
                            # Inject request_id into kwargs if possible for Langchain tools
                            result = await tool.arun(**tool_input)
                        else:
                            result = await tool.arun(tool_input)
                    return f"Tool '{tool_name}' output:\n{result}"
                except Exception as e:
                    logger.error(f"Tool execution failed: {tool_name}, error: {e}")
                    return f"Tool '{tool_name}' failed: {e}"
            else:
                return f"Tool '{tool_name}' not found."

        # Execute all tools in parallel
        if calls:
             results = await asyncio.gather(*[exec_tool(call, auth_token, request_id) for call in calls])
             outputs.extend(results)
                
        # Increment loop count
        loop_count = state.get("tool_loop_count", 0)
        
        # Append to existing scratchpad manually
        existing_scratchpad = state.get("scratchpad", []) or []
        return {
            "scratchpad": existing_scratchpad + outputs, 
            "tool_calls": [], 
            "tool_loop_count": loop_count + 1
        }

    async def node_scratchpad_summarizer(self, state: AgentState):
        """
        Summarizes long tool outputs in the scratchpad to keep context size manageable.
        Prunes outputs older than 2 turns if the total size exceeds threshold.
        """
        scratchpad = state.get("scratchpad", [])
        total_text = "\n".join(scratchpad)
        
        # Threshold: 2000 chars (approx 500 tokens)
        if len(total_text) < 2000:
            return {}

        # Prevent 400 INVALID_ARGUMENT on Flash Lite (1M token limit) 
        # JSON is dense (~1 token per 1.5-2 chars), so 1M tokens approx 1.5M chars.
        # We cap at 1M chars to be extremely safe.
        if len(total_text) > 1000000:
            logger.warning(f"Scratchpad extremely large ({len(total_text)} chars). Truncating to fit Flash Lite 1M token limit.")
            total_text = total_text[-1000000:] # Keep the most recent 1M chars

        logger.info(f"Scratchpad size ({len(total_text)}) exceeds threshold. Summarizing...")
        
        prompt = f"""
        You are a Data Compression Assistant for a Trading AI.
        The following tool outputs are too long for the context window.
        Summarize the key quantitative findings (prices, OBs, FVGs, sentiment, balance) into a concise report.
        Keep ALL critical numbers/prices. Discard formatting and redundant metadata.
        
        Tool Outputs:
        {total_text}
        
        Output: Concise Summary (Markdown)
        """
        
        try:
            # Tier 1 (3-Model Fallback)
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_lite_model_id, settings.gemini.flash_model_id, "gemini-2.0-flash-lite"],
                contents=[prompt]
            )
            summary = response.get("text", "")
            
            logger.info("Scratchpad summarized successfully.")
            # We explicitly REPLACE the scratchpad to clear the raw outputs and reset context size.
            # This works because we removed the operator.add reducer from AgentState.
            return {
                "scratchpad": [f"--- CONDENSED SUMMARY OF PREVIOUS STEPS ---\n{summary}"],
                "market_context": summary 
            }
        except Exception as e:
            logger.error(f"Summarizer failed: {e}")
            return {}

    async def node_synthesize(self, state: AgentState):
        """
        Deep Research / Synthesis Node.
        """
        query = state["optimized_query"]
        docs = state.get("retrieved_docs", [])
        
        context = "\n\n".join(docs)
        
        report = await self.gemini.generate_research_report(query, context)
        
        return {"final_response": report}

    async def node_market_scan(self, state: AgentState):
        """
        Consolidated MarketObserver logic: Parallelized Market Scan.
        """
        auth_token = state.get("auth_token")
        symbol = "XAUUSD" # Default symbol for scan
        
        logger.info("Starting Market Scan...")

        # Select tools for scan (Observer Parity)
        tools = ["smc_technical_analysis", "market_state", "get_technical_signals", "market_data", "google_search", "get_market_context"]
        
        async def run_market_tool(name):
             tool = self.tool_registry.get_tool(name)
             if not tool: return f"Tool {name} not found."
             try:
                 # Pass appropriate inputs
                 if name == "market_data": inp = {"symbol": symbol, "include_candles": False}
                 elif name == "smc_technical_analysis": inp = {"symbol": symbol, "timeframe": "H1"}
                 else: inp = symbol
                 
                 res = await tool.run(inp, auth_token=auth_token)
                 return f"### {name.replace('_', ' ').title()}\n{res}"
             except Exception as e:
                 return f"Error running {name}: {e}"

        results = await asyncio.gather(*[run_market_tool(t) for t in tools])
        
        return {
            "scratchpad": results,
            "reasoning_trace": ["System performed a comprehensive market scan for XAUUSD."]
        }

    async def node_generate_briefing(self, state: AgentState):
        """
        Consolidated DailyBriefing logic: Parallelized Personal Digest.
        Now includes macro context via Google Search.
        Includes global and individual tool timeouts to prevent Briefing Timeout.
        """
        auth_token = state.get("auth_token")
        logger.info("Generating Daily Briefing...")

        # Select tools for briefing
        is_slim = state.get("intent") == "DAILY_BRIEFING" and ("slim" in state.get("input_text", "").lower() or "lightweight" in state.get("input_text", "").lower())
        
        if is_slim:
            logger.info("Using Lightweight Briefing Mode (Slim)...")
            tools = [
                "get_account_status",
                "get_technical_signals", 
                "get_market_context",
                "smc_technical_analysis"
            ]
        else:
            tools = [
                "get_account_status",
                "get_economic_calendar", 
                "get_journal_entries",
                "get_technical_signals", 
                "get_market_context",
                "google_search",
                "smc_technical_analysis",
                "open_interest",
                "market_state"
            ]
        
        async def run_briefing_tool(name):
             tool = self.tool_registry.get_tool(name)
             if not tool:
                 logger.warning(f"Briefing Tool {name} not found.")
                 return f"Tool {name} not found."
             try:
                 inp = {}
                 if name == "get_economic_calendar": inp = {"currency": "USD", "days": 7}
                 elif name == "get_journal_entries": inp = {"limit": 5}
                 elif name == "get_technical_signals": inp = "XAUUSD"
                 elif name == "get_market_context": inp = "XAUUSD"
                 elif name == "google_search": inp = "latest XAUUSD market sentiment and news"
                 elif name == "smc_technical_analysis": inp = {"symbol": "XAUUSD", "timeframe": "H1"}
                 elif name == "open_interest": inp = {}
                 elif name == "market_state": inp = {"symbol": "XAUUSD", "timeframe": "H1"}
                 
                 # Per-tool timeout: 8 seconds
                 res = await asyncio.wait_for(tool.run(inp, auth_token=auth_token), timeout=8.0)
                 logger.info(f"Briefing Tool {name} finished. Output size: {len(res)} chars")
                 return f"### {name.replace('_', ' ').title()}\n{res}"
             except asyncio.TimeoutError:
                 logger.warning(f"⏱️ Briefing Tool {name} timed out after 8s.")
                 return f"### {name.replace('_', ' ').title()}\nTool timed out. Using previous/cached context if available."
             except Exception as e:
                 logger.error(f"Error running briefing tool {name}: {e}")
                 return f"### {name.replace('_', ' ').title()}\nError running {name}: {e}"

        # Global timeout for the entire node: 20 seconds
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[run_briefing_tool(t) for t in tools]),
                timeout=20.0
            )
        except asyncio.TimeoutError:
            logger.error("🛑 GLOBAL Briefing Timeout! Falling back to partial results.")
            # This shouldn't happen often if individual tools time out at 8s, 
            # but it's a safety net for the gather itself or node overhead.
            results = ["### Daily Briefing\nSystem was unable to gather all data in time. Please check specific tools."]

        # Filter out empty or extremely small results to avoid polluting generation
        valid_results = [r for r in results if len(r) > 50]
        if len(valid_results) < len(results):
            logger.warning(f"Some briefing tools returned empty or short results: {len(results) - len(valid_results)} failed/empty.")
        
        return {
            "scratchpad": valid_results if valid_results else results,
            "reasoning_trace": [
                "System gathered comprehensive report context: account status, calendar events, recent journal entries, technical signals, and real-time market news.",
                "Persona Instruction: Act as 'The Weaver' (Quant Fund Manager Assistant).",
                "Output Requirement: Use 'Morning Call', 'Market Focus', 'Psychological Weather', and 'Strategic Orders' structure with institutional formatting."
            ]
        }

    async def node_generate(self, state: AgentState):
        """
        Synthesizes tool results and retrieved context into a high-fidelity response.
        """
        # 0. Check for Pending Confirmation
        if state.get("pending_tool_call"):
            tool = state["pending_tool_call"]
            try:
                # Pretty print input
                inp = tool.get('tool_input')
                if isinstance(inp, str):
                    try: inp = json.loads(inp)
                    except: pass
                
                inp_str = json.dumps(inp, indent=2)
            except:
                inp_str = str(tool.get('tool_input'))

            risk_info = ""
            if tool.get("risk_analysis"):
                risk_info = f"\n\n**🛡️ Risk Analysis:**\n{tool.get('risk_analysis')}\n"

            msg = (
                f"# ⚠️ Confirmation Required\n\n"
                f"I am about to execute **{tool.get('tool_name')}**.\n\n"
                f"**Action Details:**\n```json\n{inp_str}\n```"
                f"{risk_info}\n"
                f"**Type 'YES' to confirm or 'NO' to cancel.**"
            )
            return {"final_response": msg}

        # 1. Gather Context — cap sizes to prevent 429 quota errors from 1M+ char prompts
        # scratchpad uses operator.add accumulator so can grow unboundedly across iterations
        scratchpad_raw = "\n".join(state.get("scratchpad", []))
        # Use last 20K chars — most recent tool outputs are at the end
        scratchpad = scratchpad_raw[-20000:] if len(scratchpad_raw) > 20000 else scratchpad_raw
        user_facts = "\n".join(state.get("user_facts", []))
        context_docs_raw = "\n\n".join(state.get("retrieved_docs", []))
        # Cap context docs to avoid inflating prompt
        context_docs = context_docs_raw[:10000] if len(context_docs_raw) > 10000 else context_docs_raw
        reasoning_trace = state.get("reasoning_trace", [])
        
        # Handle chat history for the prompt
        history = state.get("messages", [])
        history_str = "None."
        if history:
             recent = history[-6:] # Last 3 turns
             history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])
        
        # 2. Build Generation Prompt
        from datetime import datetime
        current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # System instructions embedded for generation
        prompt = f"""
        {SYSTEM_PERSONA}
        
        Current Date: {current_date_str}
        
        **Retrieved Context (Knowledge Base):**
        {context_docs}
        
        **Available User Information:**
        {user_facts}
        
        **Agent Planning/Reasoning:**
        {reasoning_trace[0] if reasoning_trace else "No specific reasoning plan."}
        
        **CRITICAL Tool Outputs (Execution Results):**
        {scratchpad if scratchpad else "No tools were executed."}
        
        **User Request:** "{state['optimized_query']}"
        
        **Conversation History (Working Memory):**
        {history_str}
        
        **Response Guidelines:**
        1. If Tool Outputs are present, you MUST use them as the primary source of truth for market data and prices.
        2. DO NOT use numbers from the 'Agent Planning/Reasoning' section if they conflict with 'Tool Outputs'. The reasoning section is a planning phase and may contain placeholders.
        3. Formulate a professional, quantitative response. 
        4. If no tools were used and information is missing, state it clearly.
        5. Acknowledge the conversation history if the user is asking a follow-up question.
        6. **STRICT REQUIREMENT**: You have ALREADY executed the necessary tools in a previous step. The results are in the 'CRITICAL Tool Outputs' section. DO NOT under any circumstances attempt to call or mention a tool call again. Provide a PURE TEXT response based on the results provided.
        """
        
        try:
            logger.info(f"Generating terminal response for {state['intent']}. Prompt size: {len(prompt)} chars.")
            # Tier 2 (3-Model Fallback) - Final response heavy lifting
            models = [settings.gemini.flash_model_id, settings.gemini.model_id, "gemini-2.0-flash"]
            
            # Thinking mode only if first model is a "pro" model
            thinking = None
            if "pro" in str(models[0]).lower():
                thinking = {"include_thoughts": True}
                
            result = await self.gemini.generate_content(
                model=models,
                contents=[prompt],
                thinking_config=thinking
            )
            final = result.get("text") or ""
            finish_reason = result.get("finish_reason", "STOP")
            
            if not final:
                 logger.warning(f"Gemini returned EMPTY text for query: {state['optimized_query']}. Finish Reason: {finish_reason}")
                 if finish_reason == "SAFETY":
                     final = (
                         "I'm sorry, I was unable to generate a response. The content triggered a safety filter "
                         "(likely related to financial advice restrictions). Please try rephรasing or asking for technical data only."
                     )
                 elif finish_reason == "UNEXPECTED_TOOL_CALL":
                     final = (
                         "I encountered a structural error (Unexpected Tool Call) during generation. "
                         "This happens when the model tries to call a tool in text-only mode. "
                         "Please try re-submitting your request or simplify the prompt."
                     )
                 else:
                     final = (
                         "I'm sorry, I was unable to generate a response due to a model error or service timeout. "
                         "Please try rephrasing your request."
                     )
            
            logger.info(f"Generation successful. Final response size: {len(final)} chars.")
            thoughts = result.get("thoughts") or (reasoning_trace[0] if reasoning_trace else None)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            final = f"I'm sorry, I encountered an error during generation: {e}"
            thoughts = "Generation Error"
            
        return {"final_response": final, "thoughts": thoughts}

    async def node_evaluator(self, state: AgentState):
        """
        The 'Judge' node. Evaluates if the response is complete and accurate.
        Uses Flash Lite with capped context to avoid token quota issues.
        """
        query = state["optimized_query"]
        response = state["final_response"]
        iteration = state.get("iteration_count", 0)

        if iteration >= 3:
            logger.warning(f"⚠️ Hard Safety Cap reached (Iteration {iteration}). Forcing satisfactory=True.")
            return {"is_satisfactory": True, "iteration_count": iteration + 1}

        logger.info(f"Evaluating Response (Iteration {iteration})...")

        # Cap context to avoid 429 rate limit errors
        context_raw = "\n\n".join(state.get("retrieved_docs", []))
        scratchpad_raw = "\n".join(state.get("scratchpad", []))
        context = context_raw[:3000]
        scratchpad = scratchpad_raw[-2000:]  # Only last 2000 chars

        prompt = f"""
        You are a Quality Control Judge for MTF Olympus AI.
        Evaluate if the AI response completely answers the user request.
        
        User Request: "{query}"
        
        AI Response (first 2000 chars):
        {response[:2000]}
        
        Key Tool Data (last 2000 chars):
        {scratchpad}
        
        **Output JSON only:**
        {{
            "is_satisfactory": true/false,
            "feedback": "If unsatisfactory, briefly explain what is missing. Otherwise leave empty."
        }}
        """

        try:
            # Tier 1 fallback logic
            res = await self.gemini.generate_content(
                model=[settings.gemini.flash_lite_model_id, settings.gemini.flash_model_id, "gemini-2.5-flash-lite"],
                contents=[prompt],
                response_schema=EvaluationResult
            )
            text = res.get("text", "")
            data = EvaluationResult.model_validate_json(text)
            
            return {
                "is_satisfactory": data.is_satisfactory,
                "evaluation_feedback": data.feedback or "",
                "iteration_count": iteration + 1
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # Auto-proceed on quota errors — don't block the response
            return {"is_satisfactory": True, "iteration_count": iteration + 1}

    async def node_memory_write(self, state: AgentState):
        """
        Self-Reflection: Did we learn something new about the user?
        If so, save to Long-Term Memory.
        """
        if not self.memory:
            return {}
            
        # Analyze the recent messages for facts instead of just the single turn
        messages = state.get("messages", [])
        interaction = ""
        if messages:
            # Use up to last 4 messages to get some context for the fact extraction
            recent = messages[-4:]
            interaction = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
        else:
            interaction = f"User: {state['input_text']}\nAI: {state['final_response']}"
        
        prompt = f"""
        Analyze this recent interaction. Did the user state a clear preference, goal, or fact about themselves (e.g. risk tolerance, preferred assets, trading style)?
        If yes, extract it as a concise fact (1 sentence). If no, output exactly "NO_FACT".
        
        Recent Interaction:
        {interaction}
        """
        
        try:
            # Tier 1 task
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_lite_model_id, settings.gemini.flash_model_id, "gemini-2.5-flash-lite"],
                contents=[prompt]
            )
            fact = response.get("text", "").strip()
            if "NO_FACT" not in fact and len(fact) < 200:
                await self.memory.add_user_fact(state["user_id"], fact)
        except:
             pass
        
        # Store in Semantic Cache if high quality response and NOT from cache
        intent = state.get("intent")
        if self.cache and intent in ["RESEARCH", "STRATEGY_DESIGN"] and state.get("is_satisfactory") and not state.get("from_cache"):
             await self.cache.store(state["optimized_query"], state["final_response"])
        
        # Condense History if needed (Working Memory Sliding Window)
        messages = state.get("messages", [])
        if len(messages) > 12: # 6+ turns
            logger.info(f"Messages history length ({len(messages)}) exceeded threshold. Summarizing...")
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            summary_prompt = f"""
            Summarize the key points of this conversation to be used as context for future turns.
            Focus on the user's intent, the assets discussed, and any decisions made.
            
            Conversation History:
            {history_text}
            """
            try:
                res = await self.gemini.client.aio.models.generate_content(
                    model=settings.gemini.flash_lite_model_id,
                    contents=summary_prompt
                )
                condensed = f"--- Previous Conversation Summary ---\n{res.text}"
                logger.info("Chat history condensed.")
                # We return the NEW, condensed messages array + explicitly add the newly processed turn
                # Since the reducer is operator.add, returning a NEW array will APPEND it to the checkpointed array 
                # This is tricky with operator.add. To truly truncate, we'd need a custom reducer or clear the checkpoint 
                # However, for now, we will just let LangGraph's checkpointer persist the unbounded list, 
                # but our `node_generate` and `node_query_optimizer` nodes ONLY pull the last 6 messages (recent var). 
                # This achieves the "Working Memory" sliding window effectively WITHOUT breaking operator.add semantics.
            except Exception as e:
                logger.error(f"Chat history summarization failed: {e}")
             
        # Just append the current turn to the history using the operator.add
        return {
            "messages": [
                {"role": "user", "content": state["input_text"]},
                {"role": "assistant", "content": state["final_response"]}
            ]
        }

    # --- PUBLIC API ---

    async def stream(self, input_text: str, user_id: str, auth_token: str = None, context_code: str = None, image_b64: str = None, thread_id: str = None):
        """
        Streaming entry point using LangGraph astream_events (v2).
        Yields events as they occur in the graph.
        """
        initial_state = {
            "input_text": input_text,
            "user_id": user_id,
            "auth_token": auth_token,
            "scratchpad": [],
            "retrieved_docs": [],
            "user_facts": [],
            "tool_calls": [],
            "plan_steps": [],
            "iteration_count": 0,
            "tool_loop_count": 0,
            "evaluation_feedback": "",
            "is_satisfactory": False,
            "context_code": context_code,
            "image_b64": image_b64
        }
        
        import uuid
        thread_id = thread_id or str(uuid.uuid4())
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100
        }

        # Use version="v2" for latest event schema
        async for event in self.graph.astream_events(initial_state, config=config, version="v2"):
            # Only yield relevant events to reduce bandwidth
            kind = event["event"]
            name = event["name"]
            
            # 1. Capture Node Starts (Thinking)
            if kind == "on_chain_start" and name == "LangGraph":
                 yield {"type": "status", "content": "Initializing..."}
            
            elif kind == "on_chain_start" and name in ["query_optimizer", "router", "tool_selection", "reasoning", "generate"]:
                 yield {"type": "status", "content": f"Agent {name.replace('_', ' ').title()}..."}

            # 2. Capture Tool Starts
            elif kind == "on_tool_start":
                 yield {"type": "tool_start", "tool": name, "input": event.get("data", {}).get("input")}

            # 3. Capture Token Streams (Gemini)
            elif kind == "on_chat_model_stream":
                 content = event["data"]["chunk"].content
                 if content:
                      yield {"type": "token", "content": content}

            # 4. Capture Final State (Thoughts/Response)
            elif kind == "on_chain_end" and name == "LangGraph":
                 final_state = event["data"]["output"]
                 yield {
                     "type": "final", 
                     "response": final_state.get("final_response"),
                     "thoughts": final_state.get("thoughts"),
                     "thread_id": thread_id
                 }

    async def run(self, input_text: str, user_id: str, auth_token: str = None, context_code: str = None, image_b64: str = None, thread_id: str = None):
        """
        Main entry point.
        """
        initial_state = {
            "input_text": input_text,
            "user_id": user_id,
            "auth_token": auth_token,
            "scratchpad": [],
            "retrieved_docs": [],
            "user_facts": [],
            "tool_calls": [],
            "plan_steps": [],
            "iteration_count": 0,
            "tool_loop_count": 0,
            "evaluation_feedback": "",
            "is_satisfactory": False
        }
        
        import uuid
        thread_id = thread_id or str(uuid.uuid4())
        
        # Configure Checkpoint (Ensure stateless requests don't bleed into a global user thread)
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100 # Increased for multi-step tool loops
        }
        result = await self.graph.ainvoke(initial_state, config=config)
        
        return {
            "response": result.get("final_response"),
            "thoughts": result.get("thoughts")
        }
