from typing import TypedDict, Annotated, List, Union, Any, Dict, Optional
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
from app.services.openrouter import OpenRouterClient
from app.core.config import settings
from app.core.schemas import (
    SystemToolCall,
    SystemToolSelection,
    EvaluationResult,
    SeverityClassification,
    QueryOptimization,
    PlanDecomposition,
    SentinelResult
)


from app.core.prompts import (
    SYSTEM_PERSONA, 
    RETRIEVAL_SYSTEM_PROMPT, 
    REASONING_PROMPT_TEMPLATE,
    TOOL_ROUTER_SYSTEM_PROMPT,
    STRATEGY_GENERATION_PROMPT
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
    
    # AI Analyst v2.2 - Dynamic Topology & Sentinel
    severity: str # 'ROUTINE' | 'VOLATILITY' | 'CRISIS'
    intent: str # 'chat', 'strategy_design', 'market_analysis', 'research', 'tool_use', 'briefing'
    market_severity: str
    market_context_data: dict # Renamed to avoid collision with 'market_context' string field
    sentinel_result: dict # Results from node_sentinel
    consensus_result: dict # Results from consensus_layer
    proposed_trade: dict # Captured trade proposal for sanity checking
    specialist_response: Optional[Dict[str, Any]] # Response from a specialist node

class StrategyAdvisorAgent:
    def __init__(self, 
                 rag_service: RAGService, 
                 gemini_client: GeminiClient, 
                 checkpointer: BaseCheckpointSaver = None,
                 memory_service: MemoryService = None,
                 post_mortem_agent: Any = None,
                 trade_manager_agent: Any = None):
        
        self.rag = rag_service
        self.gemini = gemini_client
        self.memory = memory_service
        self.cache = SemanticCache(gemini_client)
        self.openrouter = OpenRouterClient()
        self.checkpointer = checkpointer
        self.post_mortem = post_mortem_agent
        self.trade_manager = trade_manager_agent
        
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
        
        # v2.2 New Nodes
        workflow.add_node("severity_classifier", self.node_severity_classifier)
        workflow.add_node("sentinel", self.node_sentinel)
        workflow.add_node("consensus_layer", self.node_consensus_layer)

        # Consolidated Nodes
        workflow.add_node("market_scan", self.node_market_scan)
        workflow.add_node("generate_briefing", self.node_generate_briefing)

        workflow.add_node("market_context", self.node_market_context)
        
        # Specialist Scaling v2.5
        workflow.add_node("journal_analysis", self.node_journal_analysis)
        workflow.add_node("portfolio_management", self.node_portfolio_management)
        
        # 2. Add Edges
        workflow.set_entry_point("query_optimizer")
        
        workflow.add_edge("query_optimizer", "market_context")
        workflow.add_edge("market_context", "severity_classifier")
        workflow.add_edge("severity_classifier", "check_cache")

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
                "generate_briefing": "generate_briefing",
                "journal_analysis": "journal_analysis",
                "portfolio_management": "portfolio_management"
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
        workflow.add_edge("summarizer", "sentinel")
        
        workflow.add_conditional_edges(
            "sentinel",
            lambda x: "consensus" if x.get("severity") == "CRISIS" and x.get("sentinel_result", {}).get("approved") else "tool_use",
            {
                "consensus": "consensus_layer",
                "tool_use": "tool_selection"
            }
        )
        
        workflow.add_edge("consensus_layer", "tool_selection")
        
        workflow.add_edge("reasoning", "tool_selection") # Pass plan to tool selector
        workflow.add_edge("synthesize", "memory_write") # Research ends here usually

        # Edges for Consolidated Nodes
        workflow.add_edge("market_scan", "generate")
        workflow.add_edge("generate_briefing", "generate")
        workflow.add_edge("journal_analysis", "generate")
        workflow.add_edge("portfolio_management", "generate")
        
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

    async def node_market_context(self, state: AgentState):
        """
        Fetches real-time market context (volatility, trend) for benchmark symbols.
        Used to inform the severity classifier of current market regimes.
        """
        logger.info("Fetching real-time market context for severity assessment...")
        
        # Benchmark symbols for regime detection
        benchmarks = ["XAUUSD", "EURUSD", "BTCUSD"]
        context_results = {}
        
        try:
            # We use the registry to get the tool
            from app.core.workflow import registry
            market_tool = registry.get("get_market_context")
            
            if market_tool:
                # Run parallel fetches for benchmarks
                tasks = []
                for sym in benchmarks:
                    tasks.append(market_tool.ainvoke({"symbol": sym, "auth_token": state.get("auth_token")}))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, sym in enumerate(benchmarks):
                    res = results[i]
                    if isinstance(res, Exception):
                        logger.error(f"Failed to fetch context for {sym}: {res}")
                        continue
                    context_results[sym] = res
            
            return {"market_context_data": context_results}
        except Exception as e:
            logger.error(f"Error in node_market_context: {e}")
            return {"market_context_data": {}}

    async def node_journal_analysis(self, state: AgentState):
        """
        Orchestrates the PostMortemAgent to analyze recent trades.
        """
        logger.info("Executing Journal Analysis Specialist...")
        if not self.post_mortem:
            return {"final_response": "Post-Mortem Agent not initialized.", "intent": "CHAT"}

        try:
            # 1. Fetch unanalyzed trades via tool
            from app.core.workflow import registry
            fetch_tool = registry.get("fetch_unanalyzed_trades")
            if not fetch_tool:
                return {"final_response": "Tool 'fetch_unanalyzed_trades' not found.", "intent": "CHAT"}

            res = await fetch_tool.run_tool({"limit": 5})
            trades = res.get("trades", [])

            if not trades:
                 return {
                     "final_response": "I couldn't find any unanalyzed trades in your journal to review at this moment.",
                     "intent": "JOURNAL_ANALYSIS"
                 }

            # 2. Run specialist analysis
            analysis_results = await self.post_mortem.run_batch_analysis(trades, state["user_id"])
            
            # 3. Format result for generator
            summary = []
            for i, r in enumerate(analysis_results):
                if not r: continue
                symbol = trades[i].get("instrument") or trades[i].get("symbol", "Unknown")
                pnl = trades[i].get("realized_pnl", 0)
                summary.append(f"- {symbol} (${pnl}): {r.get('classification')} | Lesson: {r.get('critical_lesson')}")

            response_text = "### 📊 Recent Trade Post-Mortem\n\n" + "\n".join(summary)
            response_text += "\n\nInsights have been saved to your episodic memory."

            return {
                "specialist_response": {"results": analysis_results},
                "final_response": response_text,
                "intent": "JOURNAL_ANALYSIS"
            }
        except Exception as e:
            logger.error(f"Journal analysis failed: {e}")
            return {"final_response": f"Error during journal analysis: {e}", "intent": "CHAT"}

    async def node_portfolio_management(self, state: AgentState):
        """
        Orchestrates the TradeManagementAgent to actively manage positions.
        """
        logger.info("Executing Portfolio Management Specialist...")
        if not self.trade_manager:
            return {"final_response": "Trade Management Agent not initialized.", "intent": "CHAT"}

        try:
             # 1. Fetch Open Trades
             from app.core.workflow import registry
             fetch_tool = registry.get("get_account_status") # This tool returns positions
             if not fetch_tool:
                 return {"final_response": "Tool 'get_account_status' not found.", "intent": "CHAT"}

             account_data = await fetch_tool.run_tool({}, auth_token=state.get("auth_token"))
             positions = account_data.get("positions", [])

             if not positions:
                 return {
                     "final_response": "You have no open positions that require active management right now.",
                     "intent": "PORTFOLIO_MANAGEMENT"
                 }

             # 2. Run specialist management
             # We pass the market_context string from state
             market_ctx = state.get("market_context", "Normal volatility, follow standard protocol.")
             results = await self.trade_manager.manage_trades(positions, market_ctx, auth_token=state.get("auth_token"))

             # 3. Format response
             summary = []
             actions_taken = 0
             for r in results:
                 if r.get("error"):
                     summary.append(f"❌ Error managing trade {r.get('trade_id')}: {r['error']}")
                 else:
                     actions_taken += 1
                     summary.append(f"✅ {r['action']} for {r.get('trade_id')}: {r.get('reason')}")

             if actions_taken == 0:
                 response_text = "All open positions were reviewed. Based on current market context, no management actions (BE/Trailing) are required at this time."
             else:
                 response_text = "### 🛡️ Portfolio Management Actions\n\n" + "\n".join(summary)

             return {
                 "specialist_response": {"results": results},
                 "final_response": response_text,
                 "intent": "PORTFOLIO_MANAGEMENT"
             }

        except Exception as e:
            logger.error(f"Portfolio management failed: {e}")
            return {"final_response": f"Error during portfolio management: {e}", "intent": "CHAT"}

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
             formatted = []
             for msg in recent:
                 role = getattr(msg, "type", msg.get("role", "user") if isinstance(msg, dict) else "user")
                 content = getattr(msg, "content", msg.get("content", "") if isinstance(msg, dict) else str(msg))
                 formatted.append(f"{role}: {content}")
             history_str = "\n".join(formatted)
             
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
        - **JOURNAL_ANALYSIS**: User asks to analyze, review, or "post-mortem" their recent closed trades to extract lessons or psychological patterns.
        - **PORTFOLIO_MANAGEMENT**: User asks to manage, move SL to breakeven, trail stops, or actively adjust open positions/portfolio risk.
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

    async def node_severity_classifier(self, state: AgentState):
        """
        Classifies the severity of the request to determine the graph topology.
        - CRISIS: High market impact, financial danger, or adversarial conditions.
        - VOLATILITY: Market news, sentiment shifts, complex quantitative research.
        - ROUTINE: Standard chat, briefings, or simple queries.
        """
        query = state["optimized_query"]
        intent = state.get("intent", "CHAT")
        
        # Simple heuristic: TOOL_USE for trades is always at least VOLATILITY
        # But let LLM decide based on context.
        
        try:
            # Incorporate market context into the prompt
            context_summary = "No market context available."
            if state.get("market_context_data"):
                # Simplify context for LLM
                summaries = []
                for sym, data in state["market_context_data"].items():
                    vol = data.get("volatility", "unknown")
                    trend = data.get("trend_bias", "neutral")
                    summaries.append(f"{sym}: Volatility={vol}, Trend={trend}")
                context_summary = " | ".join(summaries)

            prompt = f"""
            You are a Severity Classifier for a Trading AI (MTF Olympus).
            Your goal is to classify the urgency and risk of a user query based on the query and CURRENT MARKET CONDITIONS.
            
            **Current Market Context:**
            {context_summary}

            Query: "{query}"
            Intent: {intent}
            
            **Severity Levels:**
            - **CRISIS**: Use for:
                - Asking to PLACE a live trade or large order.
                - Requests regarding flash crashes, immediate risk-of-ruin, or regime changes.
                - Anything involving direct financial execution in high-volatility markets.
            - **VOLATILITY**: Use for:
                - Market analysis on high-impact news (CPI, FOMC).
                - Complex quantitative research or strategy optimization.
                - General market outlooks that drive trading bias.
            - **ROUTINE**: Use for:
                - General chat, briefings, account status checks (balance/equity).
                - Simple technical questions or documentation retrieval.
            
            **Output JSON only:**
            {{
                "severity": "...",
                "rationale": "..."
            }}
            """
            
            logger.info(f"Severity Classification Input: {query} | Market: {context_summary}")
            
            response = await self.gemini.generate_content(
                model=[settings.gemini.flash_lite_model_id, settings.gemini.flash_model_id],
                contents=[prompt],
                response_schema=SeverityClassification
            )
            text = response.get("text", "")
            data = SeverityClassification.model_validate_json(text)
            
            logger.info(f"Severity: {data.severity} | Rationale: {data.rationale}")
            return {"severity": data.severity, "market_severity": data.severity}
        except Exception as e:
            logger.error(f"Severity classification failed: {e}")
            return {"severity": "VOLATILITY"} # Default to safe middle ground

    async def node_sentinel(self, state: AgentState):
        """
        Adversarial reviewer node. Checks for:
        1. Hallucination/Logic errors in LLM thinking.
        2. Economic Sanity Gate (Hard Python Constraints).
        """
        severity = state.get("severity", "ROUTINE")
        
        # skip for ROUTINE if no tools were called
        if severity == "ROUTINE" and not state.get("scratchpad"):
            return {"sentinel_result": {"approved": True}}

        logger.info("Sentinel Layer Reviewing state...")
        
        # 1. Economic Sanity Gate (Phase 1)
        # We look for trade proposals in the reasoning or scratchpad
        # In this version, we expect tools to populate proposed_trade if they are about to execute.
        # For now, let's implement the gate call if proposed_trade is present.
        
        proposed = state.get("proposed_trade")
        if proposed:
            from app.agents.sentinel.economic_sanity_gate import EconomicSanityGate, AccountState, TradeProposal
            from decimal import Decimal
            
            # If proposed is a string (legacy or LLM format), try to parse it
            if isinstance(proposed, str):
                try:
                    proposed = json.loads(proposed)
                except Exception:
                    logger.warning(f"Could not parse proposed_trade string: {proposed}")
                    # If it's not JSON, skip deterministic gate for now or use defaults
                    pass

            if isinstance(proposed, dict):
                # TODO: Fetch real account state via Execution Client
                # Mocking for now - this should be a tool call or service call
                account = AccountState(
                    balance=Decimal("10000"),
                    equity=Decimal("10000"),
                    margin_used=Decimal("0"),
                    open_positions=0
                )
                
                gate = EconomicSanityGate(account)
                # Map dict to TradeProposal dataclass
                try:
                    proposal = TradeProposal(
                        symbol=proposed.get("symbol", "XAUUSD"),
                        direction=proposed.get("direction", "BUY"),
                        lot_size=Decimal(str(proposed.get("lot_size", "0.01"))),
                        entry_price=Decimal(str(proposed.get("entry_price", "0"))),
                        stop_loss=Decimal(str(proposed.get("stop_loss", "0"))),
                        take_profit=Decimal(str(proposed.get("take_profit", "0")))
                    )
                    
                    is_safe, violations = gate.validate_proposal(proposal)
                    if not is_safe:
                        return {
                            "sentinel_result": {
                                "approved": False, 
                                "reason": "ECONOMIC_VIOLATION", 
                                "violations": violations
                            }
                        }
                except Exception as e:
                    logger.error(f"Sanity Gate mapping failed: {e}")
                    return {"sentinel_result": {"approved": False, "reason": "INTERNAL_ERROR"}}

        # 2. Adversarial LLM Review (Logic/Hallucination)
        # Only run full LLM sentinel for VOLATILITY and CRISIS
        if severity in ["VOLATILITY", "CRISIS"]:
            reasoning = state.get("reasoning_trace", [""])[0]
            scratchpad = "\n".join(state.get("scratchpad", []))
            proposal_str = json.dumps(proposed, indent=2) if proposed else "No trade proposed."
            
            sentinel_prompt = f"""
            You are the Sentinel Node in a Trading AI system. 
            Your job is to be ADVERSARIAL and find faults in the primary agent's logic.
            
            **Primary Agent Thinking/Reasoning:**
            {reasoning}
            
            **Tool Outputs (Market Data):**
            {scratchpad}
            
            **Final Proposal to Review:**
            {proposal_str}
            
            **Evaluation Criteria:**
            1. **Hallucination**: Is the agent using price levels not found in the market data?
            2. **Logic Conflict**: Does the reasoning say 'Bearish' but the proposal is 'BUY'?
            3. **Strategy Adherence**: Is there a Clear SMC structure (FVG, OB) mentioned and present in data?
            
            **Output JSON only:**
            {{
                "approved": boolean,
                "reason": "Clear explanation of approval or rejection",
                "risk_score": 0-100
            }}
            """
            
            try:
                sentinel_resp = await self.gemini.generate_content(
                    model=[settings.gemini.flash_model_id],
                    contents=[sentinel_prompt],
                    response_schema=SentinelResult
                )
                sentinel_data = json.loads(sentinel_resp.get("text", "{}"))
                
                if not sentinel_data.get("approved"):
                    logger.warning(f"Sentinel REJECTED proposal: {sentinel_data.get('reason')}")
                    return {"sentinel_result": sentinel_data}
                
                return {"sentinel_result": {**sentinel_data, "approved": True}}
            except Exception as e:
                logger.error(f"Sentinel LLM review failed: {e}")
                return {"sentinel_result": {"approved": True, "note": "LLM review skipped due to error"}}
            
        return {"sentinel_result": {"approved": True}}

    async def node_consensus_layer(self, state: AgentState):
        """
        Phase 2: Dual-Model Verification for CRISIS severity.
        Uses OpenRouter (Claude-3.5-Sonnet) as a secondary reviewer.
        """
        proposed = state.get("proposed_trade")
        if not proposed:
            return {"consensus_result": {"approved": True, "note": "No trade proposed for consensus."}}
        
        reasoning = state.get("reasoning_trace", [""])[0]
        scratchpad = "\n".join(state.get("scratchpad", []))
        proposal_str = json.dumps(proposed, indent=2)
        
        prompt = f"""
        You are the Second Auditor in a high-stakes Trading Consensus Protocol.
        A primary AI agent has proposed a trade during a MARKET CRISIS.
        
        **Primary Logic:**
        {reasoning}
        
        **Market Context:**
        {scratchpad}
        
        **Proposed Trade:**
        {proposal_str}
        
        **Your Task:**
        Evaluate if this trade is logical and mathematically sound given the crisis context.
        You MUST verify:
        - Direction alignment with bias.
        - Risk amount sanity.
        - Stop Loss placement logic.
        
        Output JSON only:
        {{
            "approved": boolean,
            "reason": "Technical rationale",
            "consensus_score": 0-100
        }}
        """
        
        # Call Secondary Model via OpenRouter
        model = "anthropic/claude-3.5-sonnet"
        
        try:
            response_text = await self.openrouter.generate_completion(
                model=model,
                prompt=prompt,
                system_prompt="You are a senior hedge fund risk auditor. Be extremely conservative."
            )
            consensus_data = json.loads(response_text)
            return {"consensus_result": {**consensus_data, "fallback_used": False}}
            
        except Exception as e:
            logger.warning(f"OpenRouter consensus failed: {e}. Falling back to Gemini.")
            try:
                # Gemini Fallback
                fallback_resp = await self.gemini.generate_content(
                    model=[settings.gemini.flash_model_id],
                    contents=[f"(FALLBACK AUDITOR MODE) {prompt}"],
                    config={"response_mime_type": "application/json"}
                )
                
                resp_text = fallback_resp.get("text", "{}")
                if "```json" in resp_text:
                    resp_text = resp_text.split("```json")[-1].split("```")[0].strip()
                
                fallback_data = json.loads(resp_text)
                
                # If fallback says approved is false, we should honor it
                return {
                    "consensus_result": {
                        **fallback_data, 
                        "fallback_used": True, 
                        "warning": "Warning: OpenRouter/Claude was unavailable. Verified using Gemini Fallback. Proceed with caution."
                    }
                }
            except Exception as e2:
                logger.error(f"Consensus fallback also failed: {e2}")
                return {"consensus_result": {"approved": False, "reason": f"Consensus system failure: {e2}"}}
            
        except Exception as e:
            logger.error(f"Consensus layer failed: {e}")
            return {"consensus_result": {"approved": False, "reason": f"INTERNAL_ERROR: {e}"}}

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
        severity = state.get("severity", "ROUTINE")
        
        if severity == "ROUTINE":
            if intent == "CHAT":
                return "direct"
            if intent == "TOOL_USE":
                return "tool_use"
            if intent == "MARKET_REPORT":
                return "market_scan"
            if intent == "DAILY_BRIEFING":
                return "generate_briefing"
            if intent == "JOURNAL_ANALYSIS":
                return "journal_analysis"
            if intent == "PORTFOLIO_MANAGEMENT":
                return "portfolio_management"
        
        # Default routing for VOLATILITY / CRISIS or complex ROUTINE
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
        elif intent == "JOURNAL_ANALYSIS":
            return "journal_analysis"
        elif intent == "PORTFOLIO_MANAGEMENT":
            return "portfolio_management"
        
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
        
        # 1. User Context (Long Term Memory - Hybrid v2.6)
        if self.memory:
            tasks.append(self.memory.get_adaptive_context(user_id, query))
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

        # 5. Lessons Learned (Post-Mortem Analysis)
        tasks.append(self.rag.search_lessons(query, user_id, limit=top_k))

        # Execute all retrieval tasks in parallel
        results = await asyncio.gather(*tasks)
        
        user_facts_str = results[0]
        system_docs = results[1]
        library_docs = results[2]
        strategies = results[3]
        lessons = results[4]

        user_facts = [user_facts_str] if user_facts_str and "No specific user preferences" not in user_facts_str else []
        
        # Format doc texts with explicit sources
        doc_texts = [f"[Source: {d['filename']}]\n{d['content']}" for d in system_docs]
        lib_texts = [f"[Source: Quant Library - {d['filename']}]\n{d['content']}" for d in library_docs]
        strat_texts = [f"[Strategy: {s.get('name', 'Unnamed')}]\n{s['code']}" for s in strategies]
        lesson_texts = [f"[Lesson Learned]\n{l}" for l in lessons]

        logger.info(f"✅ Retrieval complete | UserFacts: {len(user_facts)} | SystemDocs: {len(doc_texts)} | LibraryDocs: {len(lib_texts)} | Strategies: {len(strat_texts)} | Lessons: {len(lesson_texts)}")

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
            combined_docs = lesson_texts + lib_texts + doc_texts + strat_texts + refinement_ctx + [tool_ctx] + existing_docs
        else:
            combined_docs = existing_docs + [tool_ctx] + refinement_ctx + lesson_texts + doc_texts + lib_texts + strat_texts
        
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
            
            # AI Analyst v2.2 - Capture trade proposal for Sentinel review
            proposed_trade = None
            for tc in raw_tool_calls:
                if tc.get("tool_name") == "smart_order":
                    proposed_trade = tc.get("tool_input")
                    break
            
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
            
            return {
                **res_ext, 
                "tool_calls": tool_calls,
                "proposed_trade": proposed_trade
            }
            
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
                            # Note: LangChain arun takes a single input argument (dict/str)
                            result = await tool.arun(tool_input)
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
                 
                 res = await tool.arun(inp, auth_token=auth_token)
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
                 res = await asyncio.wait_for(tool.arun(inp, auth_token=auth_token), timeout=8.0)
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
             formatted = []
             for msg in recent:
                 role = getattr(msg, "type", msg.get("role", "user") if isinstance(msg, dict) else "user")
                 content = getattr(msg, "content", msg.get("content", "") if isinstance(msg, dict) else str(msg))
                 formatted.append(f"{role}: {content}")
             history_str = "\n".join(formatted)
        
        # 2. Build Generation Prompt
        strategy_standards = ""
        if state.get("intent") == "strategy_design":
            strategy_standards = f"\n{STRATEGY_GENERATION_PROMPT}\n"

        from datetime import datetime
        current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # System instructions embedded for generation
        prompt = f"""
        {SYSTEM_PERSONA}
        {strategy_standards}
        
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
        intent = state.get("intent", "CHAT")

        if iteration >= 3:
            logger.warning(f"⚠️ Hard Safety Cap reached (Iteration {iteration}). Forcing satisfactory=True.")
            return {"is_satisfactory": True, "iteration_count": iteration + 1}

        # --- Phase 4: Strategy Design Backtest Loop ---
        # If the user is asking to design or modify a strategy, we enforce a backtest check.
        # This only triggers on the first iteration to allow the tool loop to execute.
        if intent == "STRATEGY_DESIGN" and iteration == 1:
            # Check if backtest results are in the scratchpad (via backtest_runner tool)
            has_backtest = any("Backtest Results" in str(s) for s in state.get("scratchpad", [])) or "Backtest Results" in response
            
            # Identify if code or strategy parameters are being proposed
            import re
            has_code = bool(re.search(r"```python|class \w+\(Strategy\)|def next\(", response))
            
            if has_code and not has_backtest:
                logger.info("🛡️ Backtest Loop Enforcement: Strategy change detected without verification. Forcing refinement via backtest_runner.")
                return {
                    "is_satisfactory": False,
                    "evaluation_feedback": (
                        "You have proposed a strategy modification or new trading logic. "
                        "You MUST now run a 30-day backtest simulation (backtest_runner tool) "
                        "on 'XAUUSD' with the proposed parameters to verify performance. "
                        "Include the Sharpe Ratio and PnL metrics in your final recommendation."
                    ),
                    "iteration_count": iteration + 1
                }
        # ---------------------------------------------

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
            formatted = []
            for m in recent:
                role = getattr(m, "type", m.get("role", "user") if isinstance(m, dict) else "user")
                content = getattr(m, "content", m.get("content", "") if isinstance(m, dict) else str(m))
                formatted.append(f"{role}: {content}")
            interaction = "\n".join(formatted)
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
            formatted = []
            for m in messages:
                role = getattr(m, "type", m.get("role", "user") if isinstance(m, dict) else "user")
                content = getattr(m, "content", m.get("content", "") if isinstance(m, dict) else str(m))
                formatted.append(f"{role}: {content}")
            history_text = "\n".join(formatted)
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

    async def stream(self, input_text: str, user_id: str, auth_token: str = None, context_code: str = None, image_b64: str = None, thread_id: str = None, intent_hint: str = None):
        """
        Streaming entry point using LangGraph astream_events (v2).
        Yields events as they occur in the graph.
        """
        initial_state = {
            "input_text": input_text,
            "user_id": user_id,
            "auth_token": auth_token,
            "intent": intent_hint,
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
            "image_b64": image_b64,
            "severity": "ROUTINE"
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
                     "intent": final_state.get("intent"),
                     "market_severity": final_state.get("market_severity"),
                     "thread_id": thread_id
                 }

    async def run(self, input_text: str, user_id: str, auth_token: str = None, context_code: str = None, image_b64: str = None, thread_id: str = None, intent_hint: str = None):
        """
        Main entry point.
        """
        initial_state = {
            "input_text": input_text,
            "user_id": user_id,
            "auth_token": auth_token,
            "intent": intent_hint,
            "scratchpad": [],
            "retrieved_docs": [],
            "user_facts": [],
            "tool_calls": [],
            "plan_steps": [],
            "iteration_count": 0,
            "tool_loop_count": 0,
            "evaluation_feedback": "",
            "is_satisfactory": False,
            "severity": "ROUTINE"
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
            "thoughts": result.get("thoughts"),
            "intent": result.get("intent"),
            "market_severity": result.get("market_severity"),
            "metadata": result.get("metadata", {})
        }
