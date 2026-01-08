from app.core.workflow import registry
from app.tools.market import GetMarketContextTool
from app.tools.account import GetAccountStatusTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.calendar import GetEconomicCalendarTool
from app.tools.search import GoogleSearchTool
from app.tools.journal import GetJournalEntriesTool

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
    
    print("All standard tools registered.")
