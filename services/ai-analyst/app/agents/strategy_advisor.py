from typing import TypedDict, Annotated, List, Union
import operator
import json
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """
    The state of the Strategy Advisor Agent.
    """
    # Messages
    input_text: str
    user_id: str
    
    # Internal State
    optimized_query: str
    intent: str # 'chat', 'strategy_design', 'market_analysis'
    plan_steps: List[str]
    
    # Context
    retrieved_docs: Annotated[List[str], operator.add]
    user_facts: List[str]
    market_context: str
    strategy_code: str
    
    # Outputs
    reasoning_trace: List[str]
    final_response: str
    
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

        # 2. Add Edges
        workflow.set_entry_point("query_optimizer")
        
        workflow.add_edge("query_optimizer", "router")
        
        # Router Conditional API
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "direct": "generate",
                "complex": "decompose"
            }
        )
        
        workflow.add_edge("decompose", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "reasoning")
        workflow.add_edge("reasoning", "generate")
        workflow.add_edge("generate", "memory_write")
        workflow.add_edge("memory_write", END)

        # 3. Compile
        return workflow.compile(checkpointer=self.checkpointer)

    # --- NODE IMPLEMENTATIONS ---

    async def node_query_optimizer(self, state: AgentState):
        """
        Uses Gemini Flash to optimize the query.
        """
        query = state["input_text"]
        logger.info(f"Optimizing query: {query}")
        
        prompt = f"""
        You are a Query Optimizer for a Hedge Fund AI.
        Your goal is to rewrite the user's raw query into a clear, unambiguous Request.
        
        Raw Query: "{query}"
        
        1. Expand financial acronyms (e.g., "DN arb" -> "Delta Neutral Arbitrage").
        2. Identify the Intent (STRATEGY_DESIGN, MARKET_ANALYSIS, or CHAT).
        3. Output JSON only.

        Schema:
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
        Conditional Logic: Complex intent -> Decompose; Simple intent -> Direct Generate.
        """
        intent = state.get("intent", "CHAT")
        if intent in ["STRATEGY_DESIGN", "MARKET_ANALYSIS"]:
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
        
        return {
            "user_facts": user_facts,
            "retrieved_docs": doc_texts + strat_texts
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
        prompt = f"""
        Act as a Hedge Fund Quant. Follow these steps to answer the User Request.
        
        Context:
        {context}
        
        User Preferences:
        {user_facts}
        
        Plan:
        {json.dumps(steps, indent=2)}
        
        User Request: "{state['optimized_query']}"
        
        Execute the plan step-by-step. specificially cite the Context if used.
        """
        
        response = await self.gemini.client.aio.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt
        )
        
        return {"reasoning_trace": [response.text]}


    async def node_generate(self, state: AgentState):
        """
        Final Answer Generation.
        """
        # If routed directly (CHAT), we just answer. 
        # If came from Reasoning, we format the reasoning trace.
        
        if state.get("reasoning_trace"):
            # We already have the detailed answer from the Reasoning node
            final = state["reasoning_trace"][0]
        else:
            # Direct Chat Mode
            response = await self.gemini.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Answer politely and concisely: {state['optimized_query']}"
            )
            final = response.text
            
        return {"final_response": final}

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

    async def run(self, input_text: str, user_id: str, context_code: str = None, image_b64: str = None):
        """
        Main entry point.
        """
        initial_state = {
            "input_text": input_text,
            "user_id": user_id,
            "scratchpad": [],
            "retrieved_docs": [],
            "user_facts": []
        }
        
        # Configure Checkpoint (Thread ID = user_id for simplicity, or session_id)
        config = {"configurable": {"thread_id": user_id}}
        
        # Run graph
        result = await self.graph.ainvoke(initial_state, config=config)
        
        return result["final_response"]
