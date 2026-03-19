import pytest
from unittest.mock import AsyncMock, patch
from app.adapters.oanda_order import OandaOrderAdapter

@pytest.mark.asyncio
async def test_oanda_get_order_book_success():
    adapter = OandaOrderAdapter(api_key="key", account_id="123")
    
    mock_response = {
        "prices": [
            {
                "instrument": "XAU_USD",
                "bids": [{"price": "2000.50", "liquidity": 1000000}],
                "asks": [{"price": "2000.60", "liquidity": 1000000}]
            }
        ]
    }
    
    with patch("oandapyV20.endpoints.pricing.PricingInfo") as mock_info:
        mock_info.return_value.response = mock_response
        with patch("app.adapters.oanda_order.run_in_threadpool", AsyncMock()) as mock_run:
            result = await adapter.get_order_book("XAU_USD")
            
            assert "bids" in result
            assert "asks" in result
            assert result["bids"][0]["price"] == 2000.50
            assert result["asks"][0]["price"] == 2000.60
