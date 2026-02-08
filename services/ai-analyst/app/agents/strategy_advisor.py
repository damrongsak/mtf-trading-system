from typing import TypedDict, Annotated, List, Union
import operator
import json
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService

from app.core.prompts import (
    SYSTEM_PERSONA, 
    RETRIEVAL_SYSTEM_PROMPT, 
    REASONING_PROMPT_TEMPLATE,
    TOOL_ROUTER_SYSTEM_PROMPT
)
from app.core.tools import ToolRegistry, BaseTool

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

class StrategyAdvisorAgent:
    def __init__(self, 
                 rag_service: RAGService, 
                 gemini_client: GeminiClient, 
                 checkpointer: BaseCheckpointSaver = None,
                 memory_service: MemoryService = None):
        
        self.rag = rag_service
        self.gemini = gemini_client
        self.memory = memory_service
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
        workflow.add_node("memory_write", self.node_memory_write)
        
        # New Nodes for Advanced Features
        workflow.add_node("synthesize", self.node_synthesize) # Deep Research
        workflow.add_node("tool_selection", self.node_tool_selection) 
        workflow.add_node("execute_tools", self.node_execute_tools)

        # 2. Add Edges
        workflow.set_entry_point("query_optimizer")
        
        workflow.add_edge("query_optimizer", "router")
        
        # Enhanced Router Logic
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "direct": "generate",
                "complex": "decompose",
                "research": "retrieve_knowledge", # Research goes to RAG -> Synthesize
                "tool_use": "tool_selection",
                "confirmation_check": "tool_selection" # Route pending confirmations here
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

        workflow.add_edge("tool_selection", "execute_tools")
        workflow.add_edge("execute_tools", "generate") # Tools feed into generation
        
        workflow.add_edge("reasoning", "tool_selection") # Pass plan to tool selector
        workflow.add_edge("synthesize", "memory_write") # Research ends here usually
        workflow.add_edge("generate", "memory_write")
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
        
        **Intents:**
        - **TOOL_USE**: User asks for Account Balance, Trade History, or specific data lookup.
        - **RESEARCH**: User asks for deep explanation of system architecture, risk concepts, or documentation.
        - **STRATEGY_DESIGN**: User wants to code or modify a strategy.
        - **MARKET_ANALYSIS**: User asks for market outlook or price analysis.
        - **CHAT**: General conversation or simple questions.
        
        **Output JSON only:**
        {{
            "optimized_query": "...",
            "intent": "..."
        }}
        """
        
        try:
            # Use Flash model for speed
            response = await self.gemini.client.aio.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            text = response.text.replace("```json", "").replace("```", "")
            data = json.loads(text)
            
            return {
                "optimized_query": data.get("optimized_query", query),
                "intent": data.get("intent", "CHAT")
            }
        except Exception as e:
            logger.error(f"Optimizer failed: {e}")
            return {"optimized_query": query, "intent": "CHAT"}

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
        
        return "direct"

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
                model="gemini-2.5-pro", # Use Pro for reasoning
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
        
        return {
            "user_facts": user_facts,
            "retrieved_docs": doc_texts + strat_texts + [tool_ctx]
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
        
        prompt = TOOL_ROUTER_SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            query=f"{query}\n(Current Date: {current_date}){reasoning_context}"
        )
        
        try:
            response = await self.gemini.client.aio.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            text = response.text.replace("```json", "").replace("```", "")
            decision = json.loads(text)
            
            # Robust Input Extraction
            # Models sometimes use 'tool_parameters', 'parameters', or 'arguments' despite instructions
            start_input = decision.get("tool_input")
            if not start_input:
                start_input = decision.get("tool_parameters") or decision.get("parameters") or decision.get("arguments")
            
            # Update decision object for downstream use
            decision["tool_input"] = start_input

            tool_name = decision.get("tool_name")
            if tool_name == "direct_answer" or not tool_name:
                return {} 
            
            # 3. Safety Check for High-Risk Tools
            # Strategy Manager (Start/Stop) and Smart Order (Execute) need confirmation
            if tool_name in ["smart_order", "strategy_manager"]:
                # Check if it is a 'list' action for strategy, which is safe
                if tool_name == "strategy_manager":
                     inp = decision.get("tool_input", "")
                     # If input is dict and action is list, or string 'list' -> Safe
                     is_safe = False
                     if isinstance(inp, dict) and inp.get("action") == "list": is_safe = True
                     elif isinstance(inp, str) and "list" in inp.lower(): is_safe = True
                     
                     if is_safe:
                         return {"tool_calls": [decision]}

                # For Smart Order, Auto-Run Risk Check First
                if tool_name == "smart_order":
                    logger.info("Intercepting Smart Order for Risk Check...")
                    risk_tool = self.tool_registry.get_tool("risk_check")
                    token = state.get("auth_token")
                    risk_result = await risk_tool.run(decision.get("tool_input"), auth_token=token)
                    
                    # Store risk result in pending_tool_call metadata so we can show it
                    decision["risk_analysis"] = risk_result

                # Otherwise, Require Confirmation
                return {"pending_tool_call": decision, "tool_calls": []}
            
            return {"tool_calls": [decision]}
            
        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            return {}

    async def node_execute_tools(self, state: AgentState):
        """
        Executes selected tools and adds output to scratchpad.
        """
        calls = state.get("tool_calls", [])
        outputs = []
        
        auth_token = state.get("auth_token")
        
        for call in calls:
            tool_name = call.get("tool_name")
            tool_input = call.get("tool_input")
            
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                try:
                    # Execute tool
                    # Always pass auth_token
                    result = await tool.run(tool_input, auth_token=auth_token)
                    outputs.append(f"Tool '{tool_name}' output:\n{result}")
                except Exception as e:
                    outputs.append(f"Tool '{tool_name}' failed: {e}")
            else:
                outputs.append(f"Tool '{tool_name}' not found.")
                
        return {"scratchpad": outputs}

    async def node_synthesize(self, state: AgentState):
        """
        Deep Research / Synthesis Node.
        """
        query = state["optimized_query"]
        docs = state.get("retrieved_docs", [])
        
        context = "\n\n".join(docs)
        
        report = await self.gemini.generate_research_report(query, context)
        
        return {"final_response": report}


    async def node_generate(self, state: AgentState):
        """
        Final Answer Generation.
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

        thoughts = None
        final = ""
        
        # Gather Context
        scratchpad = "\n".join(state.get("scratchpad", []))
        user_facts = "\n".join(state.get("user_facts", []))
        context_docs = "\n\n".join(state.get("retrieved_docs", []))
        
        # Build System Context
        from datetime import datetime
        current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
        system_ctx = f"{SYSTEM_PERSONA}\n\nCurrent Date: {current_date_str}\n\nUser Facts:\n{user_facts}"
        
        if state.get("reasoning_trace"):
            final = state["reasoning_trace"][0]
            thoughts = "Captured from Reasoning Step (Manual CoT)"
        else:
            # Direct Chat Mode or Tool Result Synthesis
            prompt = f"""
            {system_ctx}
            
            Context from Documentation/Tools:
            {context_docs}
            
            Tool Outputs:
            {scratchpad}
            
            User Request: "{state['optimized_query']}"
            
            Answer efficiently.
            """
            
            try:
                result = await self.gemini.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    thinking_config={"include_thoughts": True} 
                )
                final = result["text"]
                thoughts = result.get("thoughts")
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                final = "I'm sorry, I encountered an error generating the response."
            
        return {"final_response": final, "thoughts": thoughts}

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
                model="gemini-2.5-flash",
                contents=prompt
            )
            fact = response.text.strip()
            if "NO_FACT" not in fact and len(fact) < 200:
                await self.memory.add_user_fact(state["user_id"], fact)
        except:
             pass
             
        return {}

    # --- PUBLIC API ---

    async def run(self, input_text: str, user_id: str, auth_token: str = None, context_code: str = None, image_b64: str = None):
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
            "plan_steps": []
        }
        
        # Configure Checkpoint (Thread ID = user_id for simplicity, or session_id)
        config = {"configurable": {"thread_id": user_id}}
        
        # Run graph
        result = await self.graph.ainvoke(initial_state, config=config)
        
        return {
            "response": result.get("final_response"),
            "thoughts": result.get("thoughts")
        }
