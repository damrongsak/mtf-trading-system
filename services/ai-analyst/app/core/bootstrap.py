from app.core.workflow import registry
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
        "oi_drift_analysis": {}
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
                    res = await tool.run(test_input, auth_token=auth_token)
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
