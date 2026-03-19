from app.core.workflow import registry
import uuid
from app.tools.market import GetMarketContextTool
from app.tools.account import GetAccountStatusTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.calendar import GetEconomicCalendarTool
from app.tools.search import GoogleSearchTool
from app.tools.journal import GetJournalEntriesTool
from app.tools.alpha_deployer import AlphaDeployerTool
from app.tools.strategy_retriever import StrategyRetrieverTool
from app.tools.open_interest import OpenInterestTool
from app.tools.market_state import MarketStateTool
from app.tools.smc import SMCAnalystTool
from app.tools.oi_drift import OpenInterestDriftTool
from app.tools.trading_plan import TradingPlanTool
from app.tools.notification import SendNotificationTool
from app.tools.shell import ShellCommandTool
from app.tools.python import PythonInterpreterTool
from app.tools.web_reader import WebReaderTool
from app.tools.skills import SkillManagerTool
from app.tools.skills_execution import ExecuteSkillTool
from app.tools.heatmap import LiquidityHeatmapTool
from app.tools.handoff import ConsultSpecialistTool
from app.tools.EconomicImpactCorrelation import EconomicImpactCorrelationTool
from app.tools.trade_modification import ModifyTradeTool
from app.tools.open_claw import OpenClawResearcherTool
from app.tools.risk import RiskReviewTool

def bootstrap_tools():
    """
    Registers all standard tools into the global registry.
    This enables UniversalAgent to find them by name string.
    """
    # Market Tools
    registry.register("get_market_context", GetMarketContextTool())
    registry.register("get_technical_signals", GetTechnicalSignalsTool())
    registry.register("get_economic_calendar", GetEconomicCalendarTool())
    
    # Account Tools
    registry.register("get_account_status", GetAccountStatusTool())
    
    # Research Tools
    registry.register("google_search", GoogleSearchTool())
    
    # Journal Tools
    registry.register("get_journal_entries", GetJournalEntriesTool())
    
    # Strategy Tools
    registry.register("deploy_alpha_strategy", AlphaDeployerTool())
    registry.register("list_active_strategies", StrategyRetrieverTool())
    registry.register("open_interest", OpenInterestTool())
    registry.register("market_state", MarketStateTool())
    registry.register("smc_technical_analysis", SMCAnalystTool())
    registry.register("oi_drift_analysis", OpenInterestDriftTool())
    registry.register("generate_trading_plan", TradingPlanTool())
    registry.register("send_notification", SendNotificationTool())

    # OS & System Tools (Approved v2.6)
    registry.register("shell_command", ShellCommandTool())
    registry.register("python_interpreter", PythonInterpreterTool())
    registry.register("web_reader", WebReaderTool())
    registry.register("save_persistent_skill", SkillManagerTool())
    registry.register("execute_skill", ExecuteSkillTool())
    registry.register("liquidity_heatmap", LiquidityHeatmapTool())
    registry.register("consult_specialist", ConsultSpecialistTool())
    registry.register("economic_impact_correlation", EconomicImpactCorrelationTool())
    registry.register("modify_trade", ModifyTradeTool())
    registry.register("open_claw_research", OpenClawResearcherTool())
    registry.register("risk_review", RiskReviewTool())
    
    print("All standard tools registered.")

async def run_diagnostics(auth_token: str = None) -> list:
    """
    Executes a smoke test for all registered tools.
    Returns a list of status objects.
    """
    results = []
    
    # Define smoke test inputs for each tool
    smoke_tests = {
        "get_market_context": "XAUUSD",
        "get_technical_signals": "XAUUSD",
        "get_economic_calendar": {"currency": "USD", "days": 1},
        "get_account_status": {},
        "google_search": "XAUUSD price today",
        "get_journal_entries": {"limit": 1},
        "deploy_alpha_strategy": None, # Skip risky or complex tools if needed
        "list_active_strategies": {"user_id": "diagnostic_user"},
        "open_interest": {},
        "market_state": "XAUUSD",
        "smc_technical_analysis": "XAUUSD",
        "oi_drift_analysis": {},
        "liquidity_heatmap": {"symbol": "XAUUSD"},
        "open_claw_research": {"task": "Verify if the Olympus research bridge is online."}
    }
    
    for name, tool in registry._tools.items():
        if name not in smoke_tests:
            continue
            
        test_input = smoke_tests[name]
        if test_input is None:
            results.append({"tool": name, "status": "SKIPPED", "message": "Smoke test not configured"})
            continue
            
        try:
            # Inject auth_token into input data for standardized pass-through
            exec_input = test_input
            if isinstance(exec_input, dict) and auth_token:
                exec_input = exec_input.copy()
                exec_input["auth_token"] = auth_token
                
            # Prioritize ainvoke for LangChain/Runnable tools
            if hasattr(tool, "ainvoke"):
                res = await tool.ainvoke(exec_input)
            elif hasattr(tool, "run"):
                try:
                    res = await tool.arun(test_input, auth_token=auth_token)
                except NotImplementedError:
                    # Fallback for LangChain tools that have a 'run' that raises this
                    if hasattr(tool, "_arun"):
                         res = await tool._arun(test_input)
                    else:
                         raise
            else:
                # Simple callable
                res = await tool(test_input)
                
            status = "SUCCESS" if "error" not in str(res).lower() and "failed" not in str(res).lower() else "FAILED"
            results.append({
                "tool": name,
                "status": status,
                "message": str(res)[:100] + "..." if len(str(res)) > 100 else str(res)
            })
        except Exception as e:
            results.append({
                "tool": name,
                "status": "ERROR",
                "message": str(e)
            })
            
    return results
