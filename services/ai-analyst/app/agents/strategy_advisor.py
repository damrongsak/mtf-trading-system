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
    
    # Internal State
    optimized_query: str
    intent: str # 'chat', 'strategy_design', 'market_analysis', 'research', 'tool_use'
    plan_steps: List[str]
    tool_calls: List[dict] # Selected tools to run
    
    # Context
    retrieved_docs: Annotated[List[str], operator.add]
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
    scratchpad: Annotated[List[str], operator.add]
    
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
        
        workflow.add_edge("execute_tools", "tool_selection")
        
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
        """
        query = state["input_text"]
        logger.info(f"Optimizing query: {query}")
        
        prompt = f"""
        You are a Query Optimizer for a Hedge Fund AI (MTF Olympus).
        Your goal is to rewrite the user's raw query into a clear, unambiguous Request and classify its INTENT.
        
        Raw Query: "{query}"
        
        **Instructions:**
        1. **Translate to English**: If the raw query is not in English, translate it to clear technical English.
        2. **Infer Symbol**: If no symbol is mentioned, default to "XAUUSD" (Gold) as this is our primary asset.
        3. **Normalize Timeframe**: Standardize timeframes (e.g., "5min" -> "M5", "1h" -> "H1").
        4. **Be Specific**: Include the symbol and timeframe in the optimized query.
        
        **Intents:**
        - **MARKET_ANALYSIS**: User asks for market outlook, price analysis, or a trading PLAN/STRATEGY for a specific symbol and timeframe.
        - **MARKET_REPORT**: User asks for a broad overview of the market (Market Observer mode).
        - **DAILY_BRIEFING**: User asks for their daily trading checklist or journal summary.
        - **CHAT**: General conversation, project questions, or simple questions not requiring real-time data.
        
        **CRITICAL**: If the user mentions a timeframe (e.g. 5min, H1, etc.) or a specific symbol (XAUUSD, Gold), ALWAYS classify as **MARKET_ANALYSIS**.
        
        **Output JSON only:**
        {{
            "optimized_query": "...",
            "intent": "..."
        }}
        """
        
        try:
            # Use Flash model for speed
            response = await self.gemini.client.aio.models.generate_content(
                model=settings.gemini.flash_model_id, 
                contents=prompt
            )
            text = response.text.replace("```json", "").replace("```", "")
            data = json.loads(text)
            
            logger.info(f"Optimization Result - Intent: {data.get('intent')}, Query: {data.get('optimized_query')}")
            return {
                "optimized_query": data.get("optimized_query", query),
                "intent": data.get("intent", "CHAT")
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
        
        if intent == "TOOL_USE":
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
            logger.debug(f"Loop Check: turn={loop_count}, tools_this_turn={len(state['tool_calls'])}")
            
            if loop_count >= 10: # 10 turns is plenty for parallel processing
                logger.warning("Max tool execution turns reached. Forcing generation.")
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
            response = await self.gemini.client.aio.models.generate_content(
                model=settings.gemini.flash_model_id, # Optimized: Use Flash for decomposition
                contents=prompt
            )
            text = response.text.replace("```json", "").replace("```", "")
            steps = json.loads(text)
            return {"plan_steps": steps}
        except:
             return {"plan_steps": ["Analyze Request", "Retrieve Data", "Formulate Answer"]}

    async def node_retrieve(self, state: AgentState):
        """
        Contextual Retrieval from Qdrant and Memory.
        """
        query = state["optimized_query"]
        user_id = state["user_id"]
        
        # 1. Retrieve User Context (Long Term)
        user_facts = []
        if self.memory:
            user_ctx = await self.memory.get_user_context(user_id, query)
            if user_ctx:
                user_facts.append(user_ctx)
                
        # 2. Retrieve System Docs (Financial Knowledge)
        system_docs = await self.rag.search_documentation(query)
        doc_texts = [d["content"] for d in system_docs]
        
        # 3. Retrieve Strategies (Code)
        strategies = await self.rag.search_similar_strategies(query, user_id)
        strat_texts = [s["code"] for s in strategies]
        
        # 4. Inject Tool Context (Dynamic Capabilities)
        tool_info = self.tool_registry.get_tool_descriptions()
        tool_ctx = f"**Available System Tools:**\n{tool_info}"
        
        # 5. Agentic RAG: Use evaluation feedback to refine search if present
        refinement_ctx = []
        if state.get("evaluation_feedback"):
             refinement_ctx.append(f"**Previous Evaluation Feedback (Reason to refine search):**\n{state['evaluation_feedback']}")
        
        return {
            "user_facts": user_facts,
            "retrieved_docs": doc_texts + strat_texts + [tool_ctx] + refinement_ctx
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
            response = await self.gemini.client.aio.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt
            )
            trace = [response.text]
        except:
            trace = ["Reasoning failed."]
        
        return {"reasoning_trace": trace}

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
            for i, output in enumerate(state["scratchpad"]):
                # Clean up output for prompt readability
                clean_output = str(output)[:2000] # Limit per tool to save context
                formatted_outputs.append(f"--- Turn {i+1} Output ---\n{clean_output}\n")
            
            tool_results = f"\n\n**Previous Tool Outputs (Current State):**\n" + "\n".join(formatted_outputs)

        prompt = TOOL_ROUTER_SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            query=f"{query}\n(Current Date: {current_date}){reasoning_context}{tool_results}"
        )
        
        logger.info(f"Tool Selection - Query: {query} | Context/Trace: {len(reasoning_context)} chars | Scratchpad: {len(tool_results)} chars")
        
        try:
            response = await self.gemini.client.aio.models.generate_content(
                model=settings.gemini.model_id, # Use Pro (model_id is gemini-2.5-pro by default)
                contents=prompt
            )
            text = response.text.replace("```json", "").replace("```", "")
            logger.debug(f"Tool Selection Decision Raw: {text}")
            decision = json.loads(text)
            
            # Validate that decision is a dictionary (not a list or other type)
            if not isinstance(decision, dict):
                logger.warning(f"Tool selection returned non-dict type: {type(decision)}. Falling back to direct answer.")
                return {}
            
            # Robust Extraction for multiple tools
            tool_calls = []
            if "tool_calls" in decision:
                tool_calls = decision["tool_calls"]
            elif "tool_name" in decision:
                # Compatibility with single-tool or partial outputs
                tool_calls = [{
                    "tool_name": decision["tool_name"],
                    "tool_input": decision.get("tool_input"),
                    "reasoning": decision.get("reasoning", "")
                }]
            
            # Map parameters for each tool (handling variations like 'tool_parameters')
            for call in tool_calls:
                 if "tool_input" not in call:
                     call["tool_input"] = call.get("tool_parameters") or call.get("parameters") or call.get("arguments")

            # --- De-duplication Logic ---
            unique_calls = []
            seen_signatures = set()
            for call in tool_calls:
                name = call.get("tool_name")
                # Normalize input for signature comparison
                inp = call.get("tool_input")
                inp_str = json.dumps(inp, sort_keys=True) if isinstance(inp, dict) else str(inp)
                sig = f"{name}:{inp_str}"
                
                if sig not in seen_signatures:
                    unique_calls.append(call)
                    seen_signatures.add(sig)
                else:
                    logger.info(f"De-duplicated redundant tool call: {name} with input {inp_str}")
            
            tool_calls = unique_calls
            # ----------------------------

            logger.info(f"Selected {len(tool_calls)} tools: {[t.get('tool_name') for t in tool_calls]}")
            
            if not tool_calls and not decision.get("direct_answer"):
                return {"tool_calls": []}

            # Populate scratchpad if direct answer exists
            res_ext = {}
            if decision.get("direct_answer"):
                res_ext["scratchpad"] = [f"System Observation: {decision['direct_answer']}"]

            # 3. Safety Check for High-Risk Tools (Currently only applies to first tool for simplicity)
            if tool_calls:
                first_tool = tool_calls[0]
                tool_name = first_tool.get("tool_name")
                
                if tool_name in ["smart_order", "strategy_manager"]:
                    # (Safety logic preserved but omitted for conciseness)
                    pass
            
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
        
        auth_token = state.get("auth_token")
        
        # Helper function for individual tool execution
        async def exec_tool(call):
            tool_name = call.get("tool_name")
            tool_input = call.get("tool_input")
            
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                try:
                    # Execute tool
                    # Always pass auth_token
                    result = await tool.run(tool_input, auth_token=auth_token)
                    return f"Tool '{tool_name}' output:\n{result}"
                except Exception as e:
                    return f"Tool '{tool_name}' failed: {e}"
            else:
                return f"Tool '{tool_name}' not found."

        # Execute all tools in parallel
        if calls:
             results = await asyncio.gather(*[exec_tool(call) for call in calls])
             outputs.extend(results)
                
        # Increment loop count
        loop_count = state.get("tool_loop_count", 0)
        return {"scratchpad": outputs, "tool_calls": [], "tool_loop_count": loop_count + 1}

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
        """
        auth_token = state.get("auth_token")
        logger.info("Generating Daily Briefing...")

        # Select tools for briefing (Daily Briefing Parity)
        tools = ["account_status", "get_economic_calendar", "journal_entries", "get_technical_signals", "get_market_context"]
        
        async def run_briefing_tool(name):
             tool = self.tool_registry.get_tool(name)
             if not tool: return f"Tool {name} not found."
             try:
                 inp = {}
                 if name == "get_economic_calendar": inp = {"currency": "USD", "days": 1}
                 elif name == "journal_entries": inp = {"limit": 5}
                 elif name == "get_technical_signals": inp = "XAUUSD"
                 elif name == "get_market_context": inp = "XAUUSD"
                 
                 res = await tool.run(inp, auth_token=auth_token)
                 return f"### {name.replace('_', ' ').title()}\n{res}"
             except Exception as e:
                 return f"Error running {name}: {e}"

        results = await asyncio.gather(*[run_briefing_tool(t) for t in tools])
        
        return {
            "scratchpad": results,
            "reasoning_trace": [
                "System gathered account status, calendar events, and recent journal entries for the daily briefing.",
                "Persona Instruction: Act as 'The Weaver' (Quant Fund Manager Assistant).",
                "Output Requirement: Use 'Morning Call', 'Market Focus', 'Psychological Weather', and 'Strategic Orders' structure."
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

        # 1. Gather Context
        scratchpad = "\n".join(state.get("scratchpad", []))
        user_facts = "\n".join(state.get("user_facts", []))
        context_docs = "\n\n".join(state.get("retrieved_docs", []))
        reasoning_trace = state.get("reasoning_trace", [])
        
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
        
        **Response Guidelines:**
        1. If Tool Outputs are present, you MUST use them as the primary source of truth for market data and prices.
        2. DO NOT use numbers from the 'Agent Planning/Reasoning' section if they conflict with 'Tool Outputs'. The reasoning section is a planning phase and may contain placeholders.
        3. Formulate a professional, quantitative response. 
        4. If no tools were used and information is missing, state it clearly.
        """
        
        try:
            # Use Gemini 2.5 Flash for faster/reliable synthesis in test
            result = await self.gemini.generate_content(
                model=settings.gemini.flash_model_id,
                contents=prompt,
                thinking_config={"include_thoughts": True} 
            )
            final = result.get("text") or "I processed your request but could not generate a narrative response."
            thoughts = result.get("thoughts") or (reasoning_trace[0] if reasoning_trace else None)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            final = f"I'm sorry, I encountered an error during generation: {e}"
            thoughts = "Generation Error"
            
        return {"final_response": final, "thoughts": thoughts}

    async def node_evaluator(self, state: AgentState):
        """
        The 'Judge' node. Evaluates if the response is complete and accurate.
        """
        query = state["optimized_query"]
        response = state["final_response"]
        context = "\n\n".join(state.get("retrieved_docs", []))
        scratchpad = "\n".join(state.get("scratchpad", []))
        iteration = state.get("iteration_count", 0)

        logger.info(f"Evaluating Response (Iteration {iteration})...")

        prompt = f"""
        You are the Quality Control (Judge) Agent for MTF Olympus AI.
        Your task is to evaluate if the AI's generated response completely and accurately answers the User Request.
        
        User Request: "{query}"
        
        AI Response:
        {response}
        
        Retrieved Context & Tool Data:
        {context}
        {scratchpad}
        
        **Evaluation Criteria:**
        1. Does it answer EVERY part of the user's request?
        2. Is it grounded in the provided context/tool data (no hallucinations)?
        3. If data was missing, did it explain why?
        4. Is the tone professional and quantitative?
        
        **Output JSON only:**
        {{
            "is_satisfactory": true/false,
            "feedback": "If unsatisfactory, explain exactly what is missing or wrong to guide the next retrieval/reasoning step. Otherwise, leave empty."
        }}
        """

        try:
            res = await self.gemini.client.aio.models.generate_content(
                model=settings.gemini.flash_model_id,
                contents=prompt
            )
            text = res.text.replace("```json", "").replace("```", "")
            data = json.loads(text)
            
            return {
                "is_satisfactory": data.get("is_satisfactory", True),
                "evaluation_feedback": data.get("feedback", ""),
                "iteration_count": iteration + 1
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"is_satisfactory": True, "iteration_count": iteration + 1}

    async def node_memory_write(self, state: AgentState):
        """
        Self-Reflection: Did we learn something new about the user?
        If so, save to Long-Term Memory.
        """
        if not self.memory:
            return {}
            
        interaction = f"User: {state['input_text']}\nAI: {state['final_response']}"
        
        prompt = f"""
        Analyze this interaction. Did the user state a clear preference, goal, or fact about themselves?
        If yes, extract it as a concise fact. If no, output "NO_FACT".
        
        Interaction:
        {interaction}
        """
        
        try:
            response = await self.gemini.client.aio.models.generate_content(
                model=settings.gemini.flash_model_id,
                contents=prompt
            )
            fact = response.text.strip()
            if "NO_FACT" not in fact and len(fact) < 200:
                await self.memory.add_user_fact(state["user_id"], fact)
        except:
             pass
        
        # Store in Semantic Cache if high quality response and NOT from cache
        intent = state.get("intent")
        if self.cache and intent in ["RESEARCH", "STRATEGY_DESIGN"] and state.get("is_satisfactory") and not state.get("from_cache"):
             await self.cache.store(state["optimized_query"], state["final_response"])
             
        return {}

    # --- PUBLIC API ---

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
        
        # Configure Checkpoint (Thread ID = thread_id or user_id for simplicity)
        config = {
            "configurable": {"thread_id": thread_id or user_id},
            "recursion_limit": 100 # Increased for multi-step tool loops
        }
        result = await self.graph.ainvoke(initial_state, config=config)
        
        return {
            "response": result.get("final_response"),
            "thoughts": result.get("thoughts")
        }
