from typing import List
from typing import List, Dict
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.trades as trades
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OandaClient:
    def __init__(self):
        if not settings.OANDA_API_KEY:
            raise ValueError("OANDA_API_KEY is not set")
        
        self.client = API(access_token=settings.OANDA_API_KEY, environment=settings.OANDA_ENV)
        self.account_id = settings.OANDA_ACCOUNT_ID

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 500, **kwargs):
        """
        Fetch OHLCV candles from Oanda.
        
        Args:
            symbol: Instrument name (e.g., 'XAU_USD')
            timeframe: Granularity (e.g., 'M15', 'H1', 'H4')
            count: Number of candles to fetch
            **kwargs: Additional parameters for Oanda API (e.g., fromTime, toTime, price, includeFirst)
        """
        # Map internal timeframes to OANDA granularities
        tf_map = {
            "D1": "D",
            "W1": "W",
            "MN1": "M"
        }
        oanda_tf = tf_map.get(timeframe, timeframe)

        params = {
            "count": count,
            "granularity": oanda_tf,
            "price": "M"  # Midpoint candles
        }
        params.update(kwargs) # Merge additional parameters
        
        try:
            # Oanda requires underscore, e.g. XAU_USD
            norm_symbol = symbol.replace('/', '_')
            logger.info(f"OANDA API Request: instrument={norm_symbol}, params={params}")
            r = instruments.InstrumentsCandles(instrument=norm_symbol, params=params)
            
            logger.info(f"Fetching OANDA candles for {symbol} | TF: {timeframe} (Mapped: {oanda_tf}) | Count: {count}")
            
            self.client.request(r)
            return r.response.get('candles', [])
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            raise e

    def get_open_positions(self) -> List[dict]:
        """
        Fetch all open trades from Oanda.
        """
        try:
            r = trades.TradesList(accountID=self.account_id, params={"state": "OPEN"})
            self.client.request(r)
            return r.response.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch open OANDA trades: {e}")
            raise e
