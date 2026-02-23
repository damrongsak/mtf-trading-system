from typing import List, Dict, Any
import json

class DataDistiller:
    """
    Utility to compress raw tool data into concise quantitative summaries
    to save context window tokens and improve reasoning speed.
    """
    
    @staticmethod
    def distill_candles(candles: List[Dict[str, Any]], count: int = 5) -> str:
        """
        Compresses a long list of candles into a snapshot summary.
        """
        if not candles:
            return "No candle data available."
            
        latest = candles[-1]
        
        # High/Low for the period
        highs = [float(c.get("high") or c.get("close") or 0) for c in candles]
        lows = [float(c.get("low") or c.get("close") or 0) for c in candles]
        
        period_high = max(highs) if highs else 0
        period_low = min(lows) if lows else 0
        
        # Take the most recent X candles
        recent = candles[-count:] if len(candles) > count else candles
        recent_str = ", ".join([f"{c.get('close') or c.get('price')}" for c in recent])
        
        return (
            f"Snapshot ({len(candles)} bins): Latest={latest.get('close') or latest.get('price')}, "
            f"High={period_high:.2f}, Low={period_low:.2f}. "
            f"Last {len(recent)} closes: [{recent_str}]"
        )

    @staticmethod
    def distill_smc_raw(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prunes complex SMC JSON data to remove redundant metadata.
        """
        # 1. Keep basic bias info
        slim_data = {
            "direction": data.get("direction"),
            "reason": data.get("reason"),
            "price": data.get("entry_price")
        }
        
        # 2. Extract only Top 2 most recent OBs per type
        analysis = data.get("analysis", {})
        obs = analysis.get("order_blocks", [])
        if obs:
            slim_obs = sorted(obs, key=lambda x: x.get("index", 0), reverse=True)[:3]
            slim_data["order_blocks"] = [
                {"type": ob.get("type"), "top": ob.get("top"), "bottom": ob.get("bottom"), "mitigated": ob.get("mitigated")}
                for ob in slim_obs
            ]
            
        # 3. Extract FVGs
        fvgs = analysis.get("fvgs", [])
        if fvgs:
             slim_fvgs = sorted(fvgs, key=lambda x: x.get("index", 0), reverse=True)[:2]
             slim_data["fvgs"] = [
                {"type": fvg.get("type"), "top": fvg.get("top"), "bottom": fvg.get("bottom")}
                for fvg in slim_fvgs
            ]
            
        return slim_data
