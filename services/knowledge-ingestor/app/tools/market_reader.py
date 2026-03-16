import requests
from typing import Dict, Any, Optional
from app.core.logger import get_logger

logger = get_logger("MarketReader")

class MarketReaderTool:
    """
    Tool for fetching real-time market data to verify document-based inferences.
    Initial implementation uses free/public APIs (e.g., Yahoo Finance via unofficial endpoints or Alpha Vantage).
    """

    @staticmethod
    def get_spot_price(symbol: str) -> Optional[float]:
        """Fetch spot price for a given symbol (e.g., XAU, BTC, AAPL)"""
        # Mapping common symbols to Yahoo Finance tickers
        mappings = {
            "Gold": "GC=F",
            "XAU": "GC=F",
            "Bitcoin": "BTC-USD",
            "BTC": "BTC-USD",
            "Silver": "SI=F",
            "XAG": "SI=F",
            "Crude Oil": "CL=F",
            "S&P 500": "^GSPC"
        }
        
        ticker = mappings.get(symbol, symbol)
        logger.info(f"🔍 Searching real-time price for: {ticker}")
        
        try:
            # Using a public finance API endpoint
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return float(price)
            else:
                logger.warning(f"Failed to fetch price for {ticker}: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error in MarketReader: {e}")
            return None

if __name__ == "__main__":
    # Test
    price = MarketReaderTool.get_spot_price("Gold")
    print(f"Current Gold Price: ${price}")
