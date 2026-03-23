import httpx
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DataPipelineClient:
    """
    Async client for communicating with the data-pipeline service.
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8001")
        self.timeout = 20.0

    async def get_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 200, 
        broker: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles for a specific symbol and timeframe.
        """
        url = f"{self.base_url}/api/v1/candles"
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "page_size": limit,
            "page": 1
        }
        if broker:
            params["broker"] = broker

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch candles from Data Pipeline for {symbol}: {e}")
            return []

    async def get_active_symbols(self, broker: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch list of active symbols from the data-pipeline.
        """
        url = f"{self.base_url}/api/v1/symbols"
        params = {}
        if broker:
            params["broker"] = broker

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch active symbols from Data Pipeline: {e}")
            return []
