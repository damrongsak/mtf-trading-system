from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any, Dict
import httpx
import os
import json

class SMCInput(BaseModel):
    symbol: str = Field(..., description="Symbol to analyze (e.g. XAU/USD, EUR/USD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. H1, 15m, 4H)")
    include_distant_zones: bool = Field(default=False, description="Set to True ONLY if macro/long-term zones are explicitly needed. False by default to save tokens.")

class SMCAnalystTool(BaseTool):
    name: str = "smc_technical_analysis"
    description: str = "Perform institutional Smart Money Concepts (SMC) technical analysis on a specific trading symbol."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> Any:
        import logging
        logger = logging.getLogger("ai-analyst")
        
        # Parse Input
        symbol = "XAUUSD"
        timeframe = "H1"
        include_distant = False
        
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                symbol = data.get("symbol", symbol)
                timeframe = data.get("timeframe", timeframe)
                include_distant = data.get("include_distant_zones", False)
            except:
                symbol = input_data.strip().upper()
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            include_distant = input_data.get("include_distant_zones", False)

        logger.info(f"--- SMC TOOL CALLED for {symbol} @ {timeframe} (Distant: {include_distant}) ---")
        
        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        # Normalize Timeframe 
        if timeframe.lower() in ["15m", "15min", "m15"]: timeframe = "M15"
        elif timeframe.lower() in ["1h", "1hr", "h1"]: timeframe = "H1"
        elif timeframe.lower() in ["4h", "4hr", "h4"]: timeframe = "H4"
        elif timeframe.lower() in ["1d", "daily", "d1"]: timeframe = "D1"

        base_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/signal/latest/{normalized_symbol}"
        
        params = {"timeframe": timeframe}
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers, timeout=15.0)
                if resp.status_code != 200: return f"Error fetching SMC analysis: {resp.status_code} - {resp.text}"
                
                data = resp.json().get("data")
                if not data: return "No data returned for SMC analysis."
                
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
                current_price_val = float(price or 0.0)
                
                global_meta = analysis.get("meta", {})
                
                # --- Dynamic Volatility Filtering ---
                # Default to 0.5% if ATR is missing, but preferably use the structural/volatility info
                atr_baseline = float(global_meta.get("atr", current_price_val * 0.005) or current_price_val * 0.005)
                # Max range is +/- 3 ATR from current price
                max_range = atr_baseline * 3.0
                upper_bound = current_price_val + max_range
                lower_bound = current_price_val - max_range

                def is_in_range(top, bottom):
                    if include_distant: return True
                    if current_price_val == 0: return True # Fallback if price missing
                    # Check if the zone overlaps with our defined ATR bounds
                    return not (bottom > upper_bound or top < lower_bound)

                raw_obs = analysis.get("order_blocks", [])
                raw_fvgs = analysis.get("fvgs", [])
                
                obs = [ob for ob in raw_obs if is_in_range(float(ob.get('top') or 0), float(ob.get('bottom') or 0))]
                fvgs = [fvg for fvg in raw_fvgs if is_in_range(float(fvg.get('top') or 0), float(fvg.get('bottom') or 0))]
                
                filtered_out = (len(raw_obs) - len(obs)) + (len(raw_fvgs) - len(fvgs))
                
                sweeps = analysis.get("liquidity_sweeps", [])
                structure = analysis.get("structure", {})
                
                if isinstance(input_data, dict) and input_data.get("slim"):
                     from app.utils.distiller import DataDistiller
                     slim_json = DataDistiller.distill_smc_raw(data)
                     return f"Slim SMC Analysis for {symbol}: {json.dumps(slim_json)}"

                # Build the professional report
                report = []
                report.append(f"### 🏛️ SMC Institutional Analysis: {symbol} ({timeframe})")
                report.append(f"\n> **📊 Data Source:** Real-time database feed from active broker connection")
                
                if not include_distant and filtered_out > 0:
                   report.append(f"> **✂️ Relevance Filter ACTIVE:** {filtered_out} distant zones hidden to save tokens. Range: {lower_bound:.2f} to {upper_bound:.2f} (+/- 3x ATR). Pass `include_distant_zones=True` for full map.")

                # Market status banner
                if market_status == "closed":
                    report.append(f"\n> [!NOTE]")
                    report.append(f"> **📊 Analysis Mode**: Historical Data Analysis")
                    report.append(f"> Markets are currently closed ({market_reason}). Analysis below uses the last available trading session from {self._format_age(data_age)} ago.")
                elif freshness == "stale":
                    report.append(f"\n> [!IMPORTANT]")
                    report.append(f"> **⚠️ Data Refresh Warning**: Latest analysis uses data from {self._format_age(data_age)} ago.")
                    if data_age > 86400 * 2:
                         report.append(f"> Note: If this is a Monday, this may reflect the weekend closure.")
                
                report.append(f"\n- **Current Rate**: {current_price_val:.2f}")
                report.append(f"- **Institutional Bias**: {direction}")
                report.append(f"- **Strategic Assessment**: {reason}")
                
                vol = float(global_meta.get("volatility_score") or 0.0)
                if global_meta:
                    report.append(f"- **Volatility Environment**: {'High' if vol > 0.005 else 'Contracting'} (Index: {vol:.4f})")

                if structure:
                    pivots = structure.get("labels", [])
                    if pivots:
                        last_p = pivots[-1]
                        last_p_price = float(last_p.get('price') or 0.0)
                        report.append(f"\n#### 📈 Market Structure Phase")
                        report.append(f"- **Current Milestone**: {last_p.get('text', 'Unknown')} detected at {last_p_price:.2f}")

                if obs:
                    report.append("\n#### 🧱 Institutional Order Blocks (OB)")
                    recent_obs = sorted(obs, key=lambda x: x.get("index", 0), reverse=True)[:3]
                    for ob in recent_obs:
                        st = ob.get("strength", "moderate")
                        meta = ob.get("meta", {})
                        ratio = meta.get("engulfing_ratio", 0)
                        mitigated = "✅ Mitigated" if ob.get("mitigated") else "⬜ FRESH/UNMITIGATED"
                        ob_type = "Supply (Bearish)" if ob.get("type") == "bearish" else "Demand (Bullish)"
                        ob_bottom = float(ob.get('bottom') or 0.0)
                        ob_top = float(ob.get('top') or 0.0)
                        
                        ob_info = f"- **{ob_type}**: {ob_bottom:.2f} - {ob_top:.2f} [{mitigated}]"
                        if ratio > 2.0:
                             ob_info += f" | 🔥 Strong Impulsive Move ({ratio:.1f}x)"
                        report.append(ob_info)
                
                if fvgs:
                    report.append("\n#### 💧 Liquidity Gaps (FVG)")
                    recent_fvgs = sorted(fvgs, key=lambda x: x.get("index", 0), reverse=True)[:2]
                    for fvg in recent_fvgs:
                         size = fvg.get("meta", {}).get("gap_size", 0)
                         fvg_type = "Inbalance (Bullish)" if fvg.get("type") == "bullish" else "Inbalance (Bearish)"
                         fvg_bottom = float(fvg.get('bottom') or 0.0)
                         fvg_top = float(fvg.get('top') or 0.0)
                         report.append(f"- **{fvg_type}**: {fvg_bottom:.2f} - {fvg_top:.2f} | Size: {abs(float(size or 0)):.2f}")


                # Generate dynamic professional outlook based on actual market conditions
                price_float = float(price or 0.0)
                price_magnitude = "high-value" if price_float > 1000 else "standard"
                bullish_confluence = global_meta.get("bullish_confluence") or []
                bearish_confluence = global_meta.get("bearish_confluence") or []
                confluence_count = len(bullish_confluence) + len(bearish_confluence)
                
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
