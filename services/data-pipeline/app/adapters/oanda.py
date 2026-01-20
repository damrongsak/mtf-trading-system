from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
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
        params = {
            "count": count,
            "granularity": timeframe,
            "price": "M"  # Midpoint candles
        }
        params.update(kwargs) # Merge additional parameters
        
        try:
            # Oanda requires underscore, e.g. XAU_USD
            norm_symbol = symbol.replace('/', '_')
            r = instruments.InstrumentsCandles(instrument=norm_symbol, params=params)
            self.client.request(r)
            return r.response.get('candles', [])
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            raise e
