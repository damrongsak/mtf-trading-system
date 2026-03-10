import sys
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

# Need to import from app context, assuming run inside container
from app.tools.market_state import MarketStateTool

class TestMarketStateTool(unittest.IsolatedAsyncioTestCase):
    @patch("aiohttp.ClientSession.get")
    async def test_risk_multiplier_high_prob(self, mock_get):
        # Mock Response for High Confluence
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "data": {
                "regime": "RANGING",
                "regime_score": 15.0,
                "fakeout_type": "SFP_LOW",
                "risk_multiplier": 1.2,
                "recommended_risk": 1.2,
                "meta": {}
            }
        }
        mock_get.return_value.__aenter__.return_value = mock_resp

        tool = MarketStateTool()
        result = await tool.arun(input_data={"symbol": "XAUUSD", "timeframe": "M15"})
        
        print(f"\n--- Output (High Prob) ---\n{result}")
        self.assertIn("**Dynamic Risk**: 1.2x (AGGRESSIVE", result)
        self.assertIn("RANGING", result)

    @patch("aiohttp.ClientSession.get")
    async def test_risk_multiplier_caution(self, mock_get):
        # Mock Response for Caution
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "data": {
                "regime": "UNSTABLE",
                "regime_score": 10.0,
                "fakeout_type": None,
                "risk_multiplier": 0.5,
                "recommended_risk": 0.5,
                "meta": {}
            }
        }
        mock_get.return_value.__aenter__.return_value = mock_resp

        tool = MarketStateTool()
        result = await tool.arun(input_data={"symbol": "XAUUSD", "timeframe": "M15"})
        
        print(f"\n--- Output (Caution) ---\n{result}")
        self.assertIn("**Dynamic Risk**: 0.5x (REDUCED SIZE", result)

if __name__ == "__main__":
    unittest.main()
