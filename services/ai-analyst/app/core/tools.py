import logging
import json
import aiohttp
import traceback
import sys
import io
import pandas as pd
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.rag import RAGService
from app.tools.smc import SMCAnalystTool
from app.tools.market_state import MarketStateTool
from app.tools.calendar import GetEconomicCalendarTool
from app.tools.journal import GetJournalEntriesTool
from app.tools.account import GetAccountStatusTool
from app.tools.strategy_retriever import StrategyRetrieverTool
from app.tools.strategy import StrategyBacktestTool
from app.tools.open_interest import OpenInterestTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.search import GoogleSearchTool
from app.tools.market import GetMarketContextTool
from app.tools.cot import COTAnalystTool
from app.tools.heatmap import LiquidityHeatmapTool
from app.tools.efp import EFPCalibrationTool
from app.tools.predictor import PredictorForecastTool, PredictorSignalTool
from app.tools.stability import SystemHealthTool
from app.tools.notification import SendNotificationTool


logger = logging.getLogger(__name__)

from app.core.base_tool import BaseTool

class KnowledgeBaseTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "Search system documentation, coding strategies, and past journal entries."
    rag_service: Any = Field(exclude=True) # Runtime dependency

    async def run(self, query: str, auth_token: str = None, request_id: str = None) -> str:
        # We assume RAG service is initialized already
        try:
            docs = await self.rag_service.search_documentation(query)
            # Maybe search strategies too if code-related
            
            context = []
            for d in docs:
                context.append(f"[Source: {d['filename']}]\n{d['content']}")
                
            return "\n\n".join(context) if context else "No relevant documentation found."
        except Exception as e:
            logger.error(f"KB Tool failed: {e}")
            return f"Error retrieving knowledge: {e}"

# AccountStatusTool and TradeHistoryTool removed (using standardized versions from app.tools)

class StrategyManagerTool(BaseTool):
    name: str = "strategy_manager"
    description: str = "\n    Manage trading strategies. \n    Action can be 'list', 'start', 'stop', or 'delete'.\n    Action 'start'/'stop' requires 'strategy_id'.\n    "

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        # Parse simple input
        action = "list"
        strategy_id = None
        
        try:
            if isinstance(input_data, str) and input_data.strip().startswith("{"):
                 try:
                    data = json.loads(input_data)
                    action = data.get("action", "list")
                    strategy_id = data.get("strategy_id")
                 except: pass
            elif isinstance(input_data, dict):
                 action = input_data.get("action", "list")
                 strategy_id = input_data.get("strategy_id")
            else:
                 parts = str(input_data).split()
                 if len(parts) > 0: action = parts[0].lower()
                 if len(parts) > 1: strategy_id = parts[1]
                 
            base_url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/strategies"
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with aiohttp.ClientSession() as session:
                if action == "list":
                    async with session.get(base_url + "/", headers=headers) as resp:
                        return await resp.text() if resp.status != 200 else json.dumps((await resp.json()).get('data', []), indent=2)
                
                elif action in ["start", "stop"]:
                    if not strategy_id: return "Error: strategy_id required for start/stop."
                    url = f"{base_url}/{strategy_id}/{action}"
                    async with session.post(url, headers=headers) as resp:
                         return f"Command {action} executed: {await resp.text()}"
                         
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Strategy Tool Error: {e}"

class BacktestRunnerTool(BaseTool):
    name: str = "backtest_runner"
    description: str = "Run a backtest on a strategy. Input JSON: {strategy_id, ...} or {symbol, timeframe...}"

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/backtest/run"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        payload = {}
        if isinstance(input_data, str):
            try: payload = json.loads(input_data)
            except: pass
        elif isinstance(input_data, dict):
            payload = input_data
            
        if not payload: return "Error: Backtest configuration payload required."

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=60.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metrics = data.get("data", {}).get("metrics", {})
                        return f"Backtest Completed.\nMetrics:\n{json.dumps(metrics, indent=2)}"
                    else:
                        return f"Backtest Failed ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Backtest Error: {e}"

class SmartOrderTool(BaseTool):
    name: str = "smart_order"
    description: str = "Place an AI-guided order. Input JSON: {symbol, direction, risk_usd, stop_loss...}"

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/execution/smart-orders"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        payload = {}
        if isinstance(input_data, str):
            try: payload = json.loads(input_data)
            except: pass
        elif isinstance(input_data, dict):
            payload = input_data
            
        if not payload: return "Error: Order details required."

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                     if resp.status == 200:
                         return f"Order Placed: {await resp.text()}"
                     else:
                         return f"Order Failed ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Order Error: {e}"

class MarketDataTool(BaseTool):
    name: str = "market_data"
    description: str = "Get market analysis, price context, and news. Input JSON: {symbol: str, timeframe: str='H1', include_candles: bool=True, include_news: bool=True, from_date: str (ISO), to_date: str (ISO)}"

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        # Parse Input
        symbol = "XAUUSD"
        timeframe = "H1"
        include_candles = False
        include_news = False
        from_date = None
        to_date = None
        
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                symbol = data.get("symbol", symbol)
                timeframe = data.get("timeframe", timeframe)
                include_candles = data.get("include_candles", True) # Default True
                include_news = data.get("include_news", True)       # Default True
                from_date = data.get("from_date")
                to_date = data.get("to_date")
            except:
                symbol = input_data.strip().upper()
                include_candles = True # Default True
                include_news = True    # Default True
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            # Robust extraction if the value itself is a dict
            if isinstance(symbol, dict):
                symbol = symbol.get("symbol") or "XAUUSD"
                
            timeframe = input_data.get("timeframe", timeframe)
            include_candles = input_data.get("include_candles", True) # Default True
            include_news = input_data.get("include_news", True)       # Default True
            from_date = input_data.get("from_date")
            to_date = input_data.get("to_date")

        # Auto-Normalization for cTrader (e.g., XAU/USD -> XAUUSD)
        if symbol and "CTRADER" in "CTRADER": # Explicit intent
             symbol = symbol.replace("/", "").replace("_", "").replace("-", "")

        report = [f"### Market Data for {symbol} ({timeframe})"]
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Create tasks for parallel execution
            tasks = []
            
            # 1. Base SMC Analysis Task
            async def get_smc():
                try:
                    url_smc = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/signal/latest/{symbol}?timeframe={timeframe}"
                    async with session.get(url_smc, headers=headers, timeout=10.0) as resp:
                         if resp.status == 200:
                             data = (await resp.json()).get("data", {})
                             return [
                                 "**SMC Analysis**:",
                                 f"- Trend Bias: {data.get('direction')}",
                                 f"- Signal Reason: {data.get('reason')}",
                                 f"- Current Price: {data.get('entry_price')}"
                             ]
                         return [f"SMC Analysis Failed ({resp.status})"]
                except Exception as e:
                    return [f"SMC Analysis Error: {e}"]

            # 2. News Task
            async def get_news():
                if not include_news: return []
                try:
                    url_news = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/news/headlines"
                    params = {"symbol": symbol, "count": 10}
                    if from_date: params["from_date"] = from_date
                    if to_date: params["to_date"] = to_date
                    
                    async with session.get(url_news, params=params, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200:
                            news_data = (await resp.json()).get("data", [])
                            res = ["**Latest News**:"]
                            if not news_data:
                                res.append("(No specific news found for this period)")
                            else:
                                for n in news_data:
                                    res.append(f"- [{n.get('published_at')}] {n.get('title')} ({n.get('source')})")
                            return res
                        return [f"News Fetch Failed ({resp.status})"]
                except Exception as e:
                    return [f"News Fetch Error: {e}"]

            # 3. Candles Task
            async def get_candles():
                if not include_candles: return []
                try:
                    url_candles = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/market/candles"
                    params = {"symbol": symbol, "timeframe": timeframe, "count": 20, "data_source": "CTRADER"}
                    async with session.get(url_candles, params=params, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200:
                            candles = (await resp.json()).get("data", [])
                            if candles:
                                df = pd.DataFrame(candles)
                                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                                try:
                                    from tabulate import tabulate
                                    table = tabulate(df, headers='keys', tablefmt='psql', showindex=False)
                                    return ["**Recent Candles (Last 20)**:", f"{table}"]
                                except Exception:
                                    return ["**Recent Candles (Last 20)**:", df.to_markdown(index=False)]
                            return ["(No candle data found)"]
                        return [f"Candle Fetch Failed ({resp.status})"]
                except Exception as e:
                    return [f"Candle Fetch Error: {e}"]

            # Run all tasks in parallel
            import asyncio
            results = await asyncio.gather(get_smc(), get_news(), get_candles())
            
            # Combine reports
            for res_list in results:
                if res_list:
                    report.extend(res_list)

        return "\n\n".join(report)

class RiskCheckTool(BaseTool):
    name: str = "risk_check"
    description: str = "Calculate trade parameters including Risk-Reward (R:R) ratio, Position Size, and Risk Amount. Use to validate trade ideas or suggest sizing."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/risk/check"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        payload = {}
        if isinstance(input_data, str):
            try: payload = json.loads(input_data)
            except: pass
        elif isinstance(input_data, dict):
            payload = input_data
            
        if not payload: return "Error: Trade details required for risk check."

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=5.0) as resp:
                     data = await resp.json()
                     if resp.status == 200:
                         return f"Risk Check PASSED.\nDetails: {json.dumps(data.get('data'), indent=2)}"
                     else:
                         return f"Risk Check FAILED ({resp.status}):\n{json.dumps(data, indent=2)}"
            except Exception as e:
                return f"Risk Check Error: {e}"

class PythonSandboxTool(BaseTool):
    name: str = "python_sandbox"
    description: str = "\n    Execute Python code for custom quantitative calculations and validation. \n    DO NOT use this tool for standard market analysis, SMC, or price forecasts if specialized tools exist.\n    Context includes 'pd', 'np'. \n    Input: Python code string. \n    Output: Standard Output of the code.\n    "

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        # Security Warning: In production, this must be sandboxed (e.g. e2b, gvisor).
        # For this MVP/Project, we run it with restricted globals.
        
        # Accept both direct code strings and dict {"code": "..."} from the AI router
        if isinstance(input_data, dict):
            code = input_data.get("code") or input_data.get("expression") or str(input_data)
        else:
            code = str(input_data)
        
        if not code.strip():
            return "Error: No code provided to execute."
        
        buffer = io.StringIO()
        sys.stdout = buffer
        
        try:
            # Prepare context with math-friendly libraries
            local_vars = {}
            exec("import pandas as pd", {}, local_vars)
            exec("import numpy as np", {}, local_vars)
            exec("import math, statistics", {}, local_vars)
            try:
                exec("from tabulate import tabulate", {}, local_vars)
            except: pass
            
            # Execute User Code
            exec(code, {}, local_vars)
            
            # Capture output
            output = buffer.getvalue()
            return output if output.strip() else "Code executed successfully (No Output)."
            
        except Exception as e:
            return f"Python Execution Error: {traceback.format_exc()}"
        finally:
            sys.stdout = sys.__stdout__ # Restore stdout


class ToolRegistry:
    def __init__(self, rag_service: RAGService):
        self.rag = rag_service
        self.tools = {
            "knowledge_base": KnowledgeBaseTool(rag_service=rag_service),
            "account_status": GetAccountStatusTool(),
            "get_account_status": GetAccountStatusTool(),
            "trade_history": GetJournalEntriesTool(),
            "journal_entries": GetJournalEntriesTool(),
            "get_journal_entries": GetJournalEntriesTool(),
            "strategy_manager": StrategyManagerTool(),
            "backtest_runner": StrategyBacktestTool(),
            "smart_order": SmartOrderTool(),
            "market_data": MarketDataTool(),
            "risk_check": RiskCheckTool(),
            "python_sandbox": PythonSandboxTool(),
            "open_interest": OpenInterestTool(),
            "smc_technical_analysis": SMCAnalystTool(),
            "market_state": MarketStateTool(),
            "send_notification": SendNotificationTool(),
            "get_economic_calendar": GetEconomicCalendarTool(),
            "get_technical_signals": GetTechnicalSignalsTool(),
            "google_search": GoogleSearchTool(),
            "get_market_context": GetMarketContextTool(),
            "list_active_strategies": StrategyRetrieverTool(),
            "cot_analyst": COTAnalystTool(),
            "liquidity_heatmap": LiquidityHeatmapTool(),
            "calibrate_efp_parameters": EFPCalibrationTool(),
            "get_predictor_forecast": PredictorForecastTool(),
            "get_predictor_signal": PredictorSignalTool(),
            "get_system_health": SystemHealthTool()
        }

    def get_tools(self) -> List[BaseTool]:
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def get_tool_descriptions(self) -> str:
        return "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
