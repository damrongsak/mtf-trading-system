from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import aiohttp
import json
from app.core.config import settings
from app.core.base_tool import BaseTool
from app.models.trade import Trade, TradeStatus, PostMortem
from app.database import SessionLocal
from sqlalchemy import select, and_

class JournalInput(BaseModel):
    limit: int = Field(default=5, description="Number of recent entries to fetch. Keep this low (5) to save tokens unless deep history is needed.")
    page: int = Field(default=1, description="Page number for pagination. Use > 1 to load older entries if the recent ones are insufficient.")

class GetJournalEntriesTool(BaseTool):
    name: str = "get_journal_entries"
    description: str = "Fetches recent trading journal entries (trades, reflections) for the user. Supports pagination."

    async def arun(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        limit = 5
        page = 1
        
        if isinstance(input_data, dict):
            limit = input_data.get("limit", 5)
            page = input_data.get("page", 1)
        elif isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                limit = data.get("limit", 5)
                page = data.get("page", 1)
            except:
                if input_data.isdigit():
                    limit = int(input_data)
            
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /journal/
                url = f"{settings.API_GATEWAY_URL}/api/v1/journal/"
                params = {"page": page, "per_page": limit}
                
                headers = {}
                if auth_token:
                    if not auth_token.startswith("Bearer "):
                        headers["Authorization"] = f"Bearer {auth_token}"
                    else:
                        headers["Authorization"] = auth_token
                
                async with session.get(url, params=params, headers=headers, timeout=3.0) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         entries = data.get("data", [])
                         
                         summary = []
                         for e in entries:
                             summary.append(f"Date: {e.get('date')} | Symbol: {e.get('symbol')} | Result: {e.get('result_pnl')} | Emotion: {e.get('emotion')}")
                         
                         return "\n".join(summary) if summary else "No journal entries found."
                     else:
                         return f"Error fetching journal ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Failed to connect to Journal Service: {e}"

class FetchTradeDetailsTool(BaseTool):
    name: str = "fetch_trade_details"
    description: str = "Fetches full institutional details for a specific trade ID."

    async def arun(self, input_data: Any, auth_token: str = None, **kwargs) -> Dict[str, Any]:
        trade_id = input_data.get("trade_id")
        if not trade_id:
            return {"error": "Missing trade_id"}
        
        try:
            with SessionLocal() as db:
                stmt = select(Trade).where(Trade.trade_id == trade_id)
                res = db.execute(stmt)
                trade = res.scalar_one_or_none()
                if not trade:
                    return {"error": f"Trade {trade_id} not found"}
                
                # Convert to dict for agent
                return {
                    "trade": {
                        "trade_id": str(trade.trade_id),
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "lot_size": float(trade.lot_size or 0),
                        "open_price": float(trade.open_price or 0),
                        "close_price": float(trade.close_price or 0),
                        "pnl_usd": float(trade.pnl_usd or 0),
                        "execution_latency_ms": float(trade.execution_latency_ms or 0),
                        "slippage_pips": float(trade.slippage_pips or 0),
                        "broker_commission": float(trade.broker_commission or 0),
                        "broker_swap": float(trade.broker_swap or 0),
                        "risk_usd": float(trade.risk_usd or 0)
                    }
                }
        except Exception as e:
            return {"error": str(e)}

class FetchUnanalyzedTradesTool(BaseTool):
    name: str = "fetch_unanalyzed_trades"
    description: str = "Fetches closed trades that do not have a post-mortem analysis yet."

    async def arun(self, input_data: Any, auth_token: str = None, **kwargs) -> Dict[str, Any]:
        limit = input_data.get("limit", 5)
        try:
            with SessionLocal() as db:
                # Subquery for trade_ids that already have post-mortems
                pm_stmt = select(PostMortem.trade_id)
                pm_res = db.execute(pm_stmt)
                analyzed_ids = [r[0] for r in pm_res.all()]
                
                # Query closed trades not in analyzed_ids
                stmt = select(Trade).where(
                    and_(
                        Trade.status == TradeStatus.CLOSED,
                        ~Trade.trade_id.in_(analyzed_ids)
                    )
                ).order_by(Trade.close_time.desc()).limit(limit)
                
                res = db.execute(stmt)
                trades = res.scalars().all()
                
                return {
                    "trades": [
                        {
                            "trade_id": str(t.trade_id),
                            "symbol": t.symbol,
                            "pnl_usd": float(t.pnl_usd or 0),
                            "execution_latency_ms": float(t.execution_latency_ms or 0),
                            "slippage_pips": float(t.slippage_pips or 0)
                        } for t in trades
                    ]
                }
        except Exception as e:
            return {"error": str(e)}

class PostMortemTool(BaseTool):
    """
    Triggers an institutional post-mortem analysis for a specific trade.
    Extracts behavioral lessons, execution quality, and psychological insights.
    """
    name: str = "run_post_mortem"
    description: str = "Analyze a closed trade to extract institutional lessons and behavioral metrics. Requires trade_id."
    
    async def arun(self, input_data: Any, auth_token: str = None, **kwargs) -> Dict[str, Any]:
        trade_id = input_data.get("trade_id")
        if not trade_id:
            return {"error": "trade_id is required"}
            
        from app.core.globals import services
        agent = services.get("post_mortem")
        if not agent:
            return {"error": "PostMortemAgent not found in registry"}
            
        # 1. Fetch trade details first
        from app.tools.journal import FetchTradeDetailsTool
        fetch_tool = FetchTradeDetailsTool()
        trade_details = await fetch_tool.arun({"trade_id": trade_id}, auth_token=auth_token)
        
        if "error" in trade_details:
            return trade_details
            
        # 2. Run analysis
        user_id = kwargs.get("user_id", "unified_user")
        analysis = await agent.analyze_trade(trade_details, user_id=user_id)
        
        if not analysis:
            return {"error": "Analysis failed to generate results"}
            
        return {
            "status": "success",
            "message": f"Post-Mortem for trade {trade_id} completed and persisted.",
            "classification": analysis.get("classification"),
            "summary": analysis.get("summary")
        }
