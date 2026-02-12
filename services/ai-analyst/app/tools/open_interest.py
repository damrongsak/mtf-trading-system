import json
import logging
from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class OpenInterestTool(BaseTool):
    name: str = "open_interest"
    description: str = """
    Fetches institutional Open Interest (OI) analysis for GOLD (XAU/USD).
    Auto-resolves to the LATEST available snapshot if date not provided.
    Input JSON: {"snapshot_at": "ISO-date", "contract": "optional-contract"}
    Returns total OI, Net OI, Put/Call Ratio, Max Pain, and OIWAP.
    """

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        url_base = f"{settings.API_GATEWAY_URL}/api/v1/data/open-interest"
        
        # Prepare Headers
        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token
        
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
                # 1. Resolve Latest Snapshot if not provided
                if not snapshot_at:
                    async with session.get(f"{url_base}/snapshots?limit=1", headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            snaps_resp = await resp.json()
                            snaps = snaps_resp.get("data", [])
                            if snaps and isinstance(snaps, list):
                                snapshot_at = snaps[0].get("snapshot_at")
                            else:
                                return "Verification: No Open Interest snapshots found in system."
                        else:
                                return f"Error: Failed to fetch snapshots ({resp.status})"

                # 2. Fetch Analysis (with Fallback Logic)
                params = {"snapshot_at": snapshot_at}
                if contract: params["contract"] = contract
                
                async def fetch_and_parse(p):
                    async with session.get(f"{url_base}/analysis", params=p, headers=headers, timeout=10.0) as r:
                         if r.status == 200:
                             return await r.json()
                         return None

                json_data = await fetch_and_parse(params)
                
                # Check for empty data if contract was specified
                data = json_data.get("data", {}) if json_data else {}
                summary = data.get("summary", {})
                total_oi = summary.get("total_call_oi", 0) + summary.get("total_put_oi", 0)
                
                is_fallback = False
                if total_oi == 0 and contract:
                    # FALLBACK: Try without contract (Aggregate Data)
                    print(f"OI Tool: Contract '{contract}' yielded 0 OI. Falling back to aggregate.")
                    params.pop("contract")
                    json_data = await fetch_and_parse(params)
                    data = json_data.get("data", {}) if json_data else {}
                    summary = data.get("summary", {})
                    total_oi = summary.get("total_call_oi", 0) + summary.get("total_put_oi", 0)
                    is_fallback = True
                
                if json_data:
                     # Parse Metrics
                     total_call = summary.get("total_call_oi", 0)
                     total_put = summary.get("total_put_oi", 0)
                     net_oi = total_call - total_put
                     pcr = summary.get("pcr", 0.0)
                     oiwap = summary.get("oiwap", 0.0)
                     
                     title = f"### Open Interest Analysis: GOLD (XAU/USD) ({snapshot_at})"
                     if is_fallback:
                         title += f"\n*(Note: Specific contract data for '{contract}' unavailable. Showing Aggregate Gold OI)*"
                     
                     report = [title]
                     report.append(f"- **Total OI**: {total_oi:,.2f}")
                     report.append(f"- **Net OI (Call-Put)**: {net_oi:,.2f}")
                     report.append(f"- **Put/Call Ratio (PCR)**: {pcr:.3f}")
                     report.append(f"- **OI Weighted Avg Price (OIWAP)**: {oiwap:,.2f}")
                     
                     # Significant Levels
                     dist = data.get("distribution", [])
                     if dist:
                         report.append("\n**Significant Liquidity Zones (Top 5)**:")
                         sorted_dist = sorted(dist, key=lambda x: (x.get("call_oi", 0) + x.get("put_oi", 0)), reverse=True)[:5]
                         for lvl in sorted_dist:
                             strike = lvl.get("strike")
                             c_oi = lvl.get("call_oi", 0)
                             p_oi = lvl.get("put_oi", 0)
                             report.append(f"- Strike {strike:.2f} | Call OI: {c_oi:,.0f} | Put OI: {p_oi:,.0f}")
                     
                     return "\n".join(report)
                else:
                    return "Error: Failed to fetch analysis data."

            except Exception as e:
                logger.error(f"OI Tool Failed: {e}")
                return f"OI Tool Error: {str(e)}"
