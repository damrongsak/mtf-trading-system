import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BinanceClient:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 1000, start_time: int = None, end_time: int = None) -> List[List[Any]]:
        """
        Fetch OHLCV candles from Binance Spot API.
        Response:
        [
          [
            1499040000000,      // Open time
            "0.01633002",       // Open
            "0.80000000",       // High
            "0.01575800",       // Low
            "0.01577100",       // Close
            "148976.11427815",  // Volume
            1499644799999,      // Close time
            ...
          ]
        ]
        """
        tf_map = {
            "M1": "1m",
            "M5": "5m",
            "M15": "15m",
            "H1": "1h",
            "H4": "4h",
            "D1": "1d",
            "W1": "1w",
            "MN1": "1M"
        }
        binance_tf = tf_map.get(timeframe)
        if not binance_tf:
            logger.error(f"Unsupported timeframe for Binance: {timeframe}")
            return []

        params = {
            "symbol": symbol.replace("/", "").replace("_", ""),
            "interval": binance_tf,
            "limit": count
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        url = f"{self.base_url}/klines"
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data
        except Exception as e:
            logger.error(f"Failed to fetch Binance candles for {symbol} ({binance_tf}): {e}")
            return []
