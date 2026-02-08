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

logger = logging.getLogger(__name__)

from app.core.base_tool import BaseTool

class KnowledgeBaseTool(BaseTool):
    name: str = "knowledge_base"
    description: str = "Search system documentation, coding strategies, and past journal entries."
    rag_service: Any = Field(exclude=True) # Runtime dependency

    async def run(self, query: str, auth_token: str = None) -> str:
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

class AccountStatusTool(BaseTool):
    name: str = "account_status"
    description: str = "Get current account balance, equity, margin, and open positions."

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        if not auth_token:
            return "Error: Authentication required for account access."

        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/execution/account/summary"
        headers = {"Authorization": f"Bearer {auth_token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Allow the agent to parse the raw JSON to be flexible
                        return json.dumps(data.get("data", {}), indent=2)
                    else:
                        text = await resp.text()
                        return f"Error ({resp.status}): {text}"
            except Exception as e:
                return f"Connection failed: {e}"

class TradeHistoryTool(BaseTool):
    name: str = "trade_history"
    description: str = "Fetch recent trade history and performance metrics."

    async def run(self, limit: int = 10, auth_token: str = None) -> str:
        if not auth_token:
            return "Error: Authentication required."
            
        # Using journal endpoint as proxy for trade history
        url = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/journal?per_page={limit}"
        headers = {"Authorization": f"Bearer {auth_token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                         data = await resp.json()
                         return json.dumps(data, indent=2)
                    return f"Error ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Connection failed: {e}"

class StrategyManagerTool(BaseTool):
    name: str = "strategy_manager"
    description: str = "\n    Manage trading strategies. \n    Action can be 'list', 'start', 'stop', or 'delete'.\n    Action 'start'/'stop' requires 'strategy_id'.\n    "

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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
            # 1. Base SMC Analysis (Existing)
            try:
                # IMPORTANT: User specifies CTRADER as default
                url_smc = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/signal/latest/{symbol}?timeframe={timeframe}"
                async with session.get(url_smc, headers=headers, timeout=10.0) as resp:
                     if resp.status == 200:
                         data = (await resp.json()).get("data", {})
                         report.append(f"**SMC Analysis**:")
                         report.append(f"- Trend Bias: {data.get('direction')}")
                         report.append(f"- Signal Reason: {data.get('reason')}")
                         report.append(f"- Current Price: {data.get('entry_price')}")
            except Exception as e:
                report.append(f"SMC Analysis Failed: {e}")

            # 2. News (New)
            if include_news:
                try:
                    url_news = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/news/headlines"
                    params = {"symbol": symbol, "count": 10}
                    if from_date: params["from_date"] = from_date
                    if to_date: params["to_date"] = to_date
                    
                    async with session.get(url_news, params=params, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200:
                            news_data = (await resp.json()).get("data", [])
                            report.append(f"**Latest News**:")
                            if not news_data:
                                report.append("(No specific news found for this period)")
                            for n in news_data:
                                report.append(f"- [{n.get('published_at')}] {n.get('title')} ({n.get('source')})")
                except Exception as e:
                    report.append(f"News Fetch Failed: {e}")

            # 3. Candles (New)
            if include_candles:
                try:
                    url_candles = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/market/candles"
                    # Defaulting to CTRADER as requested
                    params = {"symbol": symbol, "timeframe": timeframe, "count": 20, "data_source": "CTRADER"}
                    async with session.get(url_candles, params=params, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200:
                            candles = (await resp.json()).get("data", [])
                            if candles:
                                # Create compact DataFrame representation
                                df = pd.DataFrame(candles)
                                # Keep relevant columns
                                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                                report.append(f"**Recent Candles (Last 20)**:")
                                report.append(df.to_markdown(index=False))
                except Exception as e:
                    report.append(f"Candle Fetch Failed: {e}")

        return "\n\n".join(report)

class RiskCheckTool(BaseTool):
    name: str = "risk_check"
    description: str = "Pre-validate a trade idea against risk rules. Input JSON: {symbol, risk_usd, stop_loss...}"

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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

class OpenInterestTool(BaseTool):
    name: str = "open_interest"
    description: str = "\n    Get Open Interest (OI) Analysis. \n    Input JSON: {snapshot_at: str (ISO), contract: str (optional)}\n    If 'snapshot_at' is missing, it fetches the LATEST available snapshot. \n    "

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        if not auth_token: return "Error: Authentication required."
        
        url_base = f"{settings.API_GATEWAY_URL or 'http://api-gateway:8000'}/api/v1/data/open-interest"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Parse Input
        snapshot_at = None
        contract = None
        
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                snapshot_at = data.get("snapshot_at")
                contract = data.get("contract")
            except: pass
        elif isinstance(input_data, dict):
            snapshot_at = input_data.get("snapshot_at")
            contract = input_data.get("contract")

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Auto-Resolve Latest Snapshot if needed
                if not snapshot_at:
                    async with session.get(f"{url_base}/snapshots?limit=1", headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            snaps = await resp.json()
                            if isinstance(snaps, dict): snaps = snaps.get("data", [])
                            
                            if snaps and isinstance(snaps, list):
                                snapshot_at = snaps[0].get("snapshot_at")
                            else:
                                return "No Open Interest snapshots available."
                        else:
                            return f"Failed to fetch snapshots ({resp.status})."

                # 2. Fetch Analysis
                params = {"snapshot_at": snapshot_at}
                if contract: params["contract"] = contract
                
                async with session.get(f"{url_base}/analysis", params=params, headers=headers, timeout=10.0) as resp:
                    if resp.status == 200:
                         data = await resp.json()
                         if isinstance(data, dict) and "data" in data: data = data["data"]
                         
                         # Format for LLM
                         summary = [f"### Open Interest Analysis ({snapshot_at})"]
                         summary.append(f"- **Total OI**: {data.get('total_oi', 0):,}")
                         summary.append(f"- **Net OI**: {data.get('net_oi', 0):,}")
                         
                         if "put_call_ratio" in data:
                             summary.append(f"- **Put/Call Ratio**: {data.get('put_call_ratio', 0):.2f}")
                             
                         # Breakdowns
                         if "significant_levels" in data:
                             summary.append(f"\n**Significant Levels**:")
                             for lvl in data.get('significant_levels', [])[:5]:
                                 price = lvl.get('strike') or lvl.get('price')
                                 oi = (lvl.get('call_oi', 0) + lvl.get('put_oi', 0)) or lvl.get('oi', 0)
                                 summary.append(f"- {price}: {oi:,} OI")
                                 
                         return "\n".join(summary)
                    else:
                        return f"OI Analysis Failed ({resp.status}): {await resp.text()}"
                        
            except Exception as e:
                return f"Open Interest Tool Error: {e}"

class PythonSandboxTool(BaseTool):
    name: str = "python_sandbox"
    description: str = "\n    Execute Python code for data analysis. \n    Context includes 'pd', 'np'. \n    Input: Python code string. \n    Output: Standard Output of the code.\n    "

    async def run(self, code: str, auth_token: str = None) -> str:
        # Security Warning: In production, this must be sandboxed (e.g. e2b, gvisor).
        # For this MVP/Project, we run it with restricted globals.
        
        buffer = io.StringIO()
        sys.stdout = buffer
        
        try:
            # Prepare context
            local_vars = {}
            # Allow pandas and numpy
            exec("import pandas as pd", {}, local_vars)
            exec("import numpy as np", {}, local_vars)
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
            "account_status": AccountStatusTool(),
            "trade_history": TradeHistoryTool(),
            "strategy_manager": StrategyManagerTool(),
            "backtest_runner": BacktestRunnerTool(),
            "smart_order": SmartOrderTool(),
            "market_data": MarketDataTool(),
            "risk_check": RiskCheckTool(),
            "python_sandbox": PythonSandboxTool(),
            "open_interest": OpenInterestTool(),
            "smc_technical_analysis": SMCAnalystTool()
        }

    def get_tools(self) -> List[BaseTool]:
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)
    
    def get_tool_descriptions(self) -> str:
        return "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
