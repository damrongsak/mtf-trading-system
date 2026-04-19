import logging
import uuid
from typing import TypedDict, List, Dict, Any, Optional, Union
from typing_extensions import Annotated
import operator
from langchain_core.messages import BaseMessage
from langchain_core.tools import StructuredTool, BaseTool as LCTool
from app.services.gemini import GeminiClient
from app.tools.episodic_memory import SaveEpisodicMemoryTool
from app.tools.journal import FetchUnanalyzedTradesTool, FetchTradeDetailsTool, GetJournalEntriesTool, PostMortemTool

logger = logging.getLogger(__name__)

# --- State Definition (The "Wire") ---
class UserConfig(TypedDict):
    api_key: Optional[str]
    model_id: Optional[str]

class AgentState(TypedDict):
    """
    Standardized State passed between nodes in the Olympus Workflow.
    similar to n8n's JSON flow context.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_config: UserConfig
    
    # Context (RAG results, File content)
    context: Dict[str, Any]
    
    # Reasoning Trace (CoT)
    scratchpad: List[str]
    
    # Context Management
    summary: Optional[str] # Long-term conversation summary
    
    # Episodic Memory Sync
    trades_analyzed: Optional[int]
    
    # Decisions
    next_node: Optional[str]
    intent: Optional[str]
    market_severity: Optional[str]
    market_context: Optional[Dict[str, Any]]
    final_response: Optional[str]
    block_web_search: Optional[bool]


# --- Tool Registry (The "Node" Library) ---
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}

    def register(self, name: str, tool: Any, description: str = ""):
        """Register a tool instance or callable."""
        self._tools[name] = tool
        
        # Extract metadata if available (LangChain BaseTool)
        desc = description
        args = {}
        
        if hasattr(tool, "description") and not desc:
            desc = tool.description
        if hasattr(tool, "args"):
            args = tool.args
            
        self._metadata[name] = {
            "name": name,
            "description": desc,
            "args": args
        }

    def get(self, name: str) -> Any:
        return self._tools.get(name)
        
    def list_tools(self) -> List[Dict]:
        """Return list of available tools for UI."""
        return list(self._metadata.values())

    async def execute(self, name: str, **kwargs):
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        
        tool = self._tools[name]
        
        # Handle LangChain BaseTool
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(kwargs)
        elif hasattr(tool, "invoke"):
            # Fallback for sync tools if needed, but perform strictly async here ideally
            return tool.invoke(kwargs)
            
        # Handle simple callable
        return await tool(**kwargs)

# Global Registry Instance
registry = ToolRegistry()

def resolve_tools(tool_names: List[str]) -> List[LCTool]:
    """
    Standardizes tool resolution for all agents.
    Most tools are now native LangChain BaseTools.
    Non-native callables are wrapped into StructuredTools.
    """
    resolved = []
    logger.info(f"Resolving tools: {tool_names}")
    for name in tool_names:
        tool = registry.get(name)
        if not tool:
            logger.warning(f"Tool '{name}' not found.")
            continue
            
        # 1. Native LangChain Tool
        if isinstance(tool, LCTool):
            resolved.append(tool)
            continue
            
        # 2. Legacy/Simple Callable Wrap
        try:
            func = tool.run if hasattr(tool, "run") else tool
            st = StructuredTool.from_function(
                name=getattr(tool, "name", name),
                description=getattr(tool, "description", ""),
                func=func if not asyncio.iscoroutinefunction(func) else None,
                coroutine=func if asyncio.iscoroutinefunction(func) else None
            )
            resolved.append(st)
        except Exception as e:
            logger.error(f"Failed to resolve tool '{name}': {e}")
            
    logger.info(f"Successfully resolved {len(resolved)} tools.")
    return resolved

registry.register("fetch_unanalyzed_trades", FetchUnanalyzedTradesTool(), "Fetches historical closed trades missing AI Journal Entry")
registry.register("fetch_trade_details", FetchTradeDetailsTool(), "Fetches institutional details for a specific trade")
registry.register("save_episodic_memory", SaveEpisodicMemoryTool(), "Save actionable lessons for the Episodic Memory module")

from app.tools.account import GetAccountStatusTool
from app.tools.smc import SMCAnalystTool
from app.tools.market_state import MarketStateTool
from app.tools.volatility import VolatilityStructureTool
from app.tools.quant_analysis import RiskMapTool
from app.tools.journal import GetJournalEntriesTool
from app.tools.edge_optimization import EdgeOptimizationTool
from app.tools.alert import DeployTelegramAlertTool
from app.tools.open_interest import OpenInterestTool
from app.tools.cot import COTAnalystTool

registry.register("get_account_status", GetAccountStatusTool(), "Fetches account health including balance, equity, and leverage.")
registry.register("account_status", GetAccountStatusTool()) # Alias
registry.register("smc_technical_analysis", SMCAnalystTool())
registry.register("market_state", MarketStateTool())
registry.register("volatility_structure_analysis", VolatilityStructureTool())
registry.register("get_risk_map", RiskMapTool())
registry.register("get_journal_entries", GetJournalEntriesTool())
registry.register("run_post_mortem", PostMortemTool(), "Run institutional analysis on a specific trade_id")
registry.register("get_edge_optimization", EdgeOptimizationTool())
registry.register("deploy_telegram_alert", DeployTelegramAlertTool())
registry.register("open_interest", OpenInterestTool())
registry.register("cot_analyst", COTAnalystTool())

# --- Workflow Base ---
class OlympusWorkflow:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini
        self.registry = registry

    async def run_node(self, state: AgentState) -> AgentState:
        """Override this in subclasses"""
        raise NotImplementedError
