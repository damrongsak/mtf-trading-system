import asyncio
import httpx
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import json
import logging
from abc import ABC, abstractmethod

# Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
AUTH_USER = "demo1"
AUTH_PASS = "password123"
DEFAULT_SYMBOL = "XAUUSD"  # Standard ticker without underscore
DEFAULT_TIMEFRAME = "H4"  # Reverting back to institutional H4 standard

# Enhanced Symbol Mapping for Institutional Data
SYMBOL_MAP = {
    "XAU_USD": ["OGZ6", "OGQ6", "OGV6", "OGM6"],
    "XAUUSD": ["OGZ6", "OGQ6", "OGV6", "OGM6"],
    "GOLD": ["OGZ6", "OGQ6", "OGV6", "OGM6"]
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantPhysicsEngine:
    """
    Local implementation of the 'Quant Mastery' logic.
    Calculates Force, Mass, and Acceleration from raw data.
    """
    
    @staticmethod
    def calculate_force(regime_data: Dict[str, Any], sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        # Force = Trend Strength (ADX) * Sentiment Alignment
        # Standardized to 0-100 scale
        adx = float(regime_data.get("regime_score", 0.0))
        if adx == 0.0:
            # Fallback for missing ADX or insufficient bars
            adx = 15.0 # Baseline force
            
        sentiment_score = float(sentiment_data.get("sentiment", {}).get("score", 0.0))
        
        # Scaling sentiment (-1 to 1) to a multiplier (0.5 to 1.5)
        sent_mult = 1.0 + (sentiment_score * 0.5)
        
        force_val = adx * sent_mult
        
        status = "WEAK"
        if force_val > 40: status = "STRONG"
        elif force_val > 25: status = "MODERATE"
        
        return {
            "value": round(force_val, 2),
            "status": status,
            "components": {"adx": adx, "sentiment": sentiment_score}
        }

    @staticmethod
    def calculate_mass(oi_data: Dict[str, Any]) -> Dict[str, Any]:
        # Mass = Liquidity Density / Gamma Wall Concentration
        # Measured by proximity of current price to major walls
        gamma_levels = oi_data.get("gamma_levels", [])
        current_price = float(oi_data.get("price", 0.0))
        
        call_wall = 0.0
        put_wall = 0.0
        
        for level in gamma_levels:
            if level.get("type") == "CALL_WALL":
                call_wall = float(level.get("strike", 0.0))
            elif level.get("type") == "PUT_WALL":
                put_wall = float(level.get("strike", 0.0))
        
        # If no walls found, try to extract from summary
        summary = oi_data.get("summary", {})
        if call_wall == 0.0: call_wall = float(summary.get("max_call_strike", 0.0))
        if put_wall == 0.0: put_wall = float(summary.get("max_put_strike", 0.0))

        # Proximity calculation: closer walls = higher 'mass' (resistance/support)
        mass_val = 0.0
        if current_price > 0:
            if call_wall > 0:
                dist_call = abs(current_price - call_wall) / current_price
                mass_val += max(0, 1.0 - (dist_call * 10)) # High mass if < 10% away
            if put_wall > 0:
                dist_put = abs(current_price - put_wall) / current_price
                mass_val += max(0, 1.0 - (dist_put * 10))
        
        # Default unity mass if no data
        if mass_val == 0.0: mass_val = 1.0
        
        return {
            "value": round(mass_val, 2),
            "call_wall": call_wall,
            "put_wall": put_wall,
            "price": current_price
        }

    @staticmethod
    def calculate_acceleration(regime_data: Dict[str, Any]) -> Dict[str, Any]:
        # Acceleration = Change in Momentum (ADX Slope)
        slope = float(regime_data.get("adx_slope", 0.0))
        
        acc_text = "STEADY"
        if slope > 1.5: acc_text = "ACCELERATING"
        elif slope < -1.5: acc_text = "DECELERATING"
        
        return {
            "value": round(slope, 2),
            "status": acc_text
        }

class MTFQuantClient:
    def __init__(self, base_url: str = API_GATEWAY_URL):
        self.base_url = base_url
        self.token = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self):
        logger.info(f"Authenticating as {AUTH_USER}...")
        try:
            resp = await self.client.post(
                f"{self.base_url}/api/v1/auth/token",
                data={"username": AUTH_USER, "password": AUTH_PASS}
            )
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                logger.info("Authentication successful.")
            else:
                logger.error(f"Auth Failed: {resp.text}")
                raise Exception("Auth Failed")
        except Exception as e:
            logger.error(f"Connection Error: {e}")
            raise

    async def get_data(self, endpoint: str, params: dict = None) -> Dict[str, Any]:
        try:
            resp = await self.client.get(f"{self.base_url}{endpoint}", params=params)
            if resp.status_code == 200:
                # API Gateway success_response wraps data in 'data' key
                return resp.json().get("data", {})
            return {}
        except Exception as e:
            logger.warning(f"Error fetching {endpoint}: {e}")
            return {}

    async def generate_report(self, symbol: str = DEFAULT_SYMBOL, timeframe: str = DEFAULT_TIMEFRAME):
        # 1. Fetch data in parallel
        related_contracts = SYMBOL_MAP.get(symbol, [symbol])
        
        logger.info(f"Generating institutional report for {symbol} ({timeframe})...")
        
        tasks = [
            self.get_data(f"/api/v1/analysis/market-regime/{symbol}", {"timeframe": timeframe}),
            self.get_data(f"/api/v1/analysis/oi/unified-profile", {"symbol": related_contracts[0]}), # Specific contract if aggregate
            self.get_data(f"/api/v1/analysis/sentiment/cached", {"symbol": symbol}),
            self.get_data(f"/api/v1/analysis/macro/status")
        ]
        
        results = await asyncio.gather(*tasks)
        regime_data, oi_data, sentiment_data, macro_data = results
        
        # 2. Institutional Physics Calculations
        physics = QuantPhysicsEngine()
        force = physics.calculate_force(regime_data, sentiment_data)
        mass = physics.calculate_mass(oi_data)
        accel = physics.calculate_acceleration(regime_data)
        
        # 3. Format Report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_md = f"""# MTF Institutional Quantitative Report
**Asset**: {symbol} | **Timeframe**: {timeframe} | **Generated**: {timestamp}

---

## ⚡ Market Physics (Force & Mass)
*Institutional momentum is calculated as the product of Trend Strength (ADX) and Sentiment Alignment.*

| Metric | Value | Rating | Interpretation |
| :--- | :--- | :--- | :--- |
| **Market Force** (F) | {force['value']} | {force['status']} | Combined Trend + Sentiment vector. |
| **Market Mass** (m) | {mass['value']} | { 'HEAVY' if mass['value'] > 1.2 else 'LIGHT' } | Proximity and density of institutional liquidity walls. |
| **Acceleration** (a) | {accel['value']} | {accel['status']} | Rate of change in momentum (ADX Slope). |

---

## 🛡️ Microstructure Profile (Gamma)
*Liquidity walls derived from top-tier Option Open Interest.*

- **Current Reference**: {mass['price']}
- **Call Wall (Resistance)**: {mass['call_wall'] if mass['call_wall'] > 0 else 'N/A: No Data'}
- **Put Wall (Support)**: {mass['put_wall'] if mass['put_wall'] > 0 else 'N/A: No Data'}
- **Gamma Regime**: {oi_data.get("gamma_regime", "UNKNOWN")}

---

## 🧩 Sentiment & Macro Context
- **AI Sentiment Score**: {sentiment_data.get("sentiment", {}).get("score", "N/A")} ({sentiment_data.get("sentiment", {}).get("reason", "No cache found")})
- **Macro Status**: 
    - **DXY (Dollar)**: {macro_data.get("dxy", {}).get("value", "N/A")}
    - **VIX (Equity Risk)**: {macro_data.get("vix", {}).get("value", "N/A")}
    - **GVZ (Gold Vol)**: {macro_data.get("gvz", {}).get("value", "N/A")}

---

## 📋 Executive Summary
The market is currently in a **{regime_data.get("regime", "UNSTABLE")}** regime. 
With a Force of **{force['value']}** and { 'positive' if accel['value'] > 0 else 'negative' } acceleration, institutional participants are currently **{ 'active' if force['value'] > 20 else 'inactive' }**. 
{'WARNING: Proximity to major liquidity walls detected.' if mass['value'] > 1.3 else 'Liquidity distribution is currently sparse.'}

---
*Confidentiality Notice: Distributed under MTF Institutional License.*
"""
        # Save to file
        os.makedirs("scripts/client/reports", exist_ok=True)
        filename = f"scripts/client/reports/daily_report_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, "w") as f:
            f.write(report_md)
        
        logger.info(f"Report saved to {filename}")
        print("\n" + "="*50)
        print("INSTITUTIONAL QUANT REPORT")
        print("="*50)
        print(report_md)

    async def close(self):
        await self.client.aclose()

async def main():
    client = MTFQuantClient()
    try:
        await client.authenticate()
        await client.generate_report()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
