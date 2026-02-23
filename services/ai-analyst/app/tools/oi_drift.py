import json
import logging
from typing import Any, Optional, Dict, List
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenInterestDriftTool(BaseTool):
    name: str = "oi_drift_analysis"
    description: str = """
    Analyzes the 'Drift' or shifts in institutional Open Interest (OI) for Gold.
    Compares the latest snapshot with the previous one (usually 24h apart).
    Detects:
    - Sentiment Drift (Change in Net OI / PCR)
    - Wall Migration (Movement of Call/Put Walls)
    - Gamma Flip Shift (Pivot movement)
    
    Use this during session opens (London/NY) to see how positioning has changed overnight.
    """

    async def run(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        url_base = f"{settings.API_GATEWAY_URL}/api/v1/data/open-interest"
        
        # Prepare Headers
        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token
        
        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Latest 2 Snapshots
                async with session.get(f"{url_base}/snapshots?limit=2", headers=headers, timeout=5.0) as resp:
                    if resp.status != 200:
                        return f"Error: Failed to fetch snapshots ({resp.status})"
                    
                    snaps_resp = await resp.json()
                    snaps = snaps_resp.get("data", [])
                    if len(snaps) < 2:
                        return "Insufficient data: Need at least 2 OI snapshots to perform drift analysis."
                    
                    latest_ts = snaps[0].get("snapshot_at")
                    prev_ts = snaps[1].get("snapshot_at")

                # 2. Fetch Analysis for both
                async def fetch_analysis(ts):
                    params = {"snapshot_at": ts}
                    async with session.get(f"{url_base}/analysis", params=params, headers=headers, timeout=10.0) as r:
                        if r.status == 200:
                            res = await r.json()
                            return res.get("data", {})
                        return None

                latest_analysis = await fetch_analysis(latest_ts)
                prev_analysis = await fetch_analysis(prev_ts)

                if not latest_analysis or not prev_analysis:
                    return "Error: Failed to fetch analysis data for comparison."

                # 3. Perform Drift Calculation
                lat_sum = latest_analysis.get("summary", {})
                pre_sum = prev_analysis.get("summary", {})

                # Sentiment Drift
                lat_pcr = float(lat_sum.get("pcr") or 1.0)
                pre_pcr = float(pre_sum.get("pcr") or 1.0)
                pcr_drift = lat_pcr - pre_pcr
                
                lat_net = float(lat_sum.get("total_call_oi") or 0.0) - float(lat_sum.get("total_put_oi") or 0.0)
                pre_net = float(pre_sum.get("total_call_oi") or 0.0) - float(pre_sum.get("total_put_oi") or 0.0)
                net_drift = lat_net - pre_net

                # Wall Migration
                lat_cw = float(lat_sum.get("max_call_strike") or 0.0)
                pre_cw = float(pre_sum.get("max_call_strike") or 0.0)
                cw_shift = lat_cw - pre_cw
                
                lat_pw = float(lat_sum.get("max_put_strike") or 0.0)
                pre_pw = float(pre_sum.get("max_put_strike") or 0.0)
                pw_shift = lat_pw - pre_pw

                # 4. Build Report
                report = [f"### 🌊 Gold Open Interest Drift Analysis"]
                report.append(f"\n> Comparing snapshots: **{prev_ts[:16]}** ⮕ **{latest_ts[:16]}**")
                
                # Sentiment Section
                sentiment_icon = "📈" if net_drift > 0 else "📉"
                report.append(f"\n#### {sentiment_icon} Institutional Sentiment Drift")
                report.append(f"- **PCR Shift**: {pre_pcr:.3f} ⮕ {lat_pcr:.3f} ({'+' if pcr_drift > 0 else ''}{pcr_drift:.3f})")
                report.append(f"- **Net OI Delta**: {net_drift:,.0f} units ({'Bullish Build' if net_drift > 0 else 'Bearish Build'})")

                # Wall Migration Section
                report.append(f"\n#### 🧱 Liquidity Wall Migration")
                
                cw_desc = "Neutral/Static"
                if cw_shift > 0: cw_desc = f"🔺 Moving UP to {lat_cw} (Higher Resistance)"
                elif cw_shift < 0: cw_desc = f"🔻 Moving DOWN to {lat_cw} (Lower Resistance - BEARISH)"
                report.append(f"- **Call Wall (Resistance)**: {cw_desc}")

                pw_desc = "Neutral/Static"
                if pw_shift > 0: pw_desc = f"🔺 Moving UP to {lat_pw} (Higher Support - BULLISH)"
                elif pw_shift < 0: pw_desc = f"🔻 Moving DOWN to {lat_pw} (Lower Support)"
                report.append(f"- **Put Wall (Support)**: {pw_desc}")

                # Summary Remark
                remark = "Institutional positioning is stable."
                if net_drift > 5000 and (cw_shift >= 0 and pw_shift >= 0):
                    remark = "Strong Bullish Drift detected: Markets shifting liquidity targets higher."
                elif net_drift < -5000 and (cw_shift <= 0 and pw_shift <= 0):
                    remark = "Strong Bearish Drift detected: Defensive positioning increasing at lower levels."
                
                report.append(f"\n> [!TIP]\n> **Market Observation**: {remark}")

                return "\n".join(report)

            except Exception as e:
                logger.error(f"OI Drift Tool Failed: {e}")
                return f"OI Drift Tool Error: {str(e)}"
