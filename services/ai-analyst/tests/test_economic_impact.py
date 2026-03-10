import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.EconomicImpactCorrelation import EconomicImpactCorrelationTool
from app.core.config import settings

@pytest.mark.asyncio
async def test_economic_impact_correlation_success():
    tool = EconomicImpactCorrelationTool()
    
    # Mock data-pipeline response
    with patch("httpx.AsyncClient.get") as mock_get:
        # 1. Calendar Response
        mock_calendar_resp = MagicMock()
        mock_calendar_resp.status_code = 200
        mock_calendar_resp.json.return_value = [
            {"title": "Non-Farm Payrolls", "datetime": "2024-01-01T13:30:00Z", "country": "USD", "impact": "High"}
        ]
        
        # 2. Candles Response
        mock_candles_resp = MagicMock()
        mock_candles_resp.status_code = 200
        mock_candles_resp.json.return_value = {
            "items": [
                {"timestamp": "2024-01-01T13:25:00Z", "high": 2000.0, "low": 1990.0},
                {"timestamp": "2024-01-01T13:30:00Z", "high": 2030.0, "low": 2000.0},
                {"timestamp": "2024-01-01T13:35:00Z", "high": 2020.0, "low": 2010.0},
            ]
        }
        
        mock_get.side_effect = [mock_calendar_resp, mock_candles_resp]
        
        result = await tool.run_tool({
            "symbol": "XAUUSD",
            "currency": "USD",
            "impact": "High",
            "lookback_days": 1
        })
        
        assert "Volatility Correlation Analysis" in result
        assert "Non-Farm Payrolls" in result
        assert "Avg Volatility $40.00" in result # 2030 - 1990 (max/min in window)
        assert "RECOMMENDED NO-TRADE" in result

@pytest.mark.asyncio
async def test_economic_impact_no_events():
    tool = EconomicImpactCorrelationTool()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_calendar_resp = MagicMock()
        mock_calendar_resp.status_code = 200
        mock_calendar_resp.json.return_value = []
        mock_get.return_value = mock_calendar_resp
        
        result = await tool.run_tool({"lookback_days": 1})
        assert "No High impact events found" in result
