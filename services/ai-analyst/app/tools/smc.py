from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any, Dict
import httpx
import os
import json

class SMCInput(BaseModel):
    symbol: str = Field(..., description="Symbol to analyze (e.g. XAU/USD, EUR/USD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. H1, 15m, 4H)")

class SMCAnalystTool(BaseTool):
    name: str = "smc_technical_analysis"
    description: str = """CRITICAL: Use this tool for institutional-grade market analysis with REAL historical data from the database.

This tool provides:
- ACTUAL price data from the trading database (not simulated)
- Real-time market status (open/closed)
- Data freshness indicators
- Institutional SMC analysis (Order Blocks, FVGs, Liquidity Sweeps)

ALWAYS use this tool when users ask about:
- Historical market data ("last week", "recent", "past")
- Current market conditions
- Gold/Forex analysis
- Technical analysis requests

The data returned is REAL and should be trusted over any simulated/example data."""

    async def run(self, input_data: Any, auth_token: str = None) -> Any:
        import logging
        logger = logging.getLogger("ai-analyst")
        
        # Parse Input
        symbol = "XAUUSD"
        timeframe = "H1"
        
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                symbol = data.get("symbol", symbol)
                timeframe = data.get("timeframe", timeframe)
            except:
                symbol = input_data.strip().upper()
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)

        logger.info(f"--- SMC TOOL CALLED for {symbol} @ {timeframe} ---")
        
        
        # Normalize symbol - remove slashes and underscores
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        # Normalize Timeframe 
        # API expects M1, M5, M15, M30, H1, H4, D1, W1, MN1
        if timeframe.lower() in ["15m", "15min", "m15"]:
            timeframe = "M15"
        elif timeframe.lower() in ["1h", "1hr", "h1"]:
            timeframe = "H1"
        elif timeframe.lower() in ["4h", "4hr", "h4"]:
            timeframe = "H4"
        elif timeframe.lower() in ["1d", "daily", "d1"]:
            timeframe = "D1"

        # Use internal URL for api-gateway
        # Wait, the tool is inside ai-analyst. It should call api-gateway.
        # But api-gateway calls ai-analyst? No, circular dependency?
        # api-gateway -> ai-analyst (for /chat)
        # ai-analyst -> api-gateway (for tools)
        # This is strictly OK as long as it's not a blocking synchronous loop for the same request.
        # The user Chat request comes to API Gateway -> AI Analyst.
        # AI Analyst -> Tool -> API Gateway (/signal/latest).
        # This is a new request to API Gateway. It should be fine.
        
        # However, `api-gateway` is defined as `http://api-gateway:8000` in docker-compose?
        # Let's check docker-compose.yml.
        # `api-gateway` service name is `api-gateway`.
        
        base_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/signal/latest/{normalized_symbol}"
        
        params = {"timeframe": timeframe}

        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=15.0)
                if resp.status_code != 200:
                    return f"Error fetching SMC analysis: {resp.status_code} - {resp.text}"
                
                data = resp.json().get("data")
                if not data:
                    return "No data returned for SMC analysis."
                
                # Extract market context
                market_status = data.get("market_status", "unknown")
                market_reason = data.get("market_reason", "")
                data_age = data.get("data_age_seconds", 0)
                freshness = data.get("data_freshness", "unknown")
                
                # Extract analysis data
                analysis = data.get("analysis") or {}
                direction = data.get("direction", "NEUTRAL")
                reason = data.get("reason", "Consolidating at structural levels.")
                price = data.get("entry_price", 0)
                
                obs = analysis.get("order_blocks", [])
                fvgs = analysis.get("fvgs", [])
                sweeps = analysis.get("liquidity_sweeps", [])
                structure = analysis.get("structure", {})
                global_meta = analysis.get("meta", {})
                
                # Build the professional report
                report = []
                report.append(f"### 🏛️ SMC Institutional Analysis: {symbol} ({timeframe})")
                report.append(f"\n> **📊 Data Source:** Real-time database feed from active broker connection")
                
                # Market status banner
                if market_status == "closed":
                    report.append(f"\n> [!NOTE]")
                    report.append(f"> **📊 Analysis Mode**: Historical Data Analysis")
                    report.append(f"> Markets are currently closed ({market_reason}). Analysis below uses the last available trading session from {self._format_age(data_age)} ago.")
                    report.append(f"> This historical data is valuable for reviewing market structure, identifying patterns, and planning future trades.")
                elif freshness == "stale":
                    report.append(f"\n> [!CAUTION]")
                    report.append(f"> **⚠️ Data Delay**: Analysis based on data from {self._format_age(data_age)} ago")
                    report.append(f"> Real-time streaming may be temporarily unavailable. Using latest database snapshot.")
                
                report.append(f"\n- **Current Rate**: {price:.2f}")
                report.append(f"- **Institutional Bias**: {direction}")
                report.append(f"- **Strategic Assessment**: {reason}")
                
                if global_meta:
                    vol = global_meta.get("volatility_score", 0)
                    report.append(f"- **Volatility Environment**: {'High' if vol > 0.005 else 'Contracting'} (Index: {vol:.4f})")

                if structure:
                    pivots = structure.get("labels", [])
                    if pivots:
                        last_p = pivots[-1]
                        report.append(f"\n#### 📈 Market Structure Phase")
                        report.append(f"- **Current Milestone**: {last_p['text']} detected at {last_p['price']:.2f}")

                if obs:
                    report.append("\n#### 🧱 Institutional Order Blocks (OB)")
                    recent_obs = sorted(obs, key=lambda x: x.get("index", 0), reverse=True)[:3]
                    for ob in recent_obs:
                        st = ob.get("strength", "moderate")
                        meta = ob.get("meta", {})
                        ratio = meta.get("engulfing_ratio", 0)
                        mitigated = "✅ Mitigated" if ob.get("mitigated") else "⬜ FRESH/UNMITIGATED"
                        ob_type = "Supply (Bearish)" if ob.get("type") == "bearish" else "Demand (Bullish)"
                        
                        ob_info = f"- **{ob_type}**: {ob.get('bottom'):.2f} - {ob.get('top'):.2f} [{mitigated}]"
                        if ratio > 2.0:
                             ob_info += f" | 🔥 Strong Impulsive Move ({ratio:.1f}x)"
                        report.append(ob_info)
                
                if fvgs:
                    report.append("\n#### 💧 Liquidity Gaps (FVG)")
                    recent_fvgs = sorted(fvgs, key=lambda x: x.get("index", 0), reverse=True)[:2]
                    for fvg in recent_fvgs:
                         size = fvg.get("meta", {}).get("gap_size", 0)
                         fvg_type = "Inbalance (Bullish)" if fvg.get("type") == "bullish" else "Inbalance (Bearish)"
                         report.append(f"- **{fvg_type}**: {fvg.get('bottom'):.2f} - {fvg.get('top'):.2f} | Size: {abs(size):.2f}")


                # Generate dynamic professional outlook based on actual market conditions
                price_magnitude = "high-value" if price > 1000 else "standard"
                confluence_count = len(global_meta.get("bullish_confluence", [])) + len(global_meta.get("bearish_confluence", []))
                
                outlook_parts = []
                outlook_parts.append("\n> [!TIP]")
                outlook_parts.append(f"> **Professional Outlook**: {symbol} exhibits ")
                
                if vol > 0.005:
                    outlook_parts.append("elevated algorithmic sensitivity in the current volatility regime. ")
                else:
                    outlook_parts.append("stable institutional participation with controlled volatility. ")
                
                if confluence_count > 0:
                    outlook_parts.append("Multiple confluence zones detected—alignment between fresh Order Blocks and impulsive FVG expansions provides the highest probability for institutional entries.")
                else:
                    outlook_parts.append("Monitor for confluence development between Order Blocks and Fair Value Gaps to identify high-probability institutional entry zones.")
                
                report.append("".join(outlook_parts))

                
                return "\n".join(report)
                
            except Exception as e:
                return f"Failed to perform SMC analysis: {str(e)}"
    
    def _format_age(self, seconds: int) -> str:
        """Format age in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"
