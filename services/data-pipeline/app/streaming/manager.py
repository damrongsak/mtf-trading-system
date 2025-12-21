from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.data_source import DataSource
from app.streaming.adapters.oanda import OandaStreamer
from app.streaming.publisher import RedisPublisher
import logging

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self):
        self.publisher = RedisPublisher()
        self.adapters = {} # name -> adapter instance

    async def start(self):
        logger.info("Starting StreamManager...")
        await self.publisher.connect()
        
        # Load configs
        db = SessionLocal()
        try:
            data_sources = db.query(DataSource).filter(DataSource.is_active == True).all()
            logger.info(f"Found {len(data_sources)} active data sources")
            
            for ds in data_sources:
                if ds.name.lower() == 'oanda':
                    self._start_oanda(ds.config_json)
                # Add other adapters here (e.g. Binance)
                
        except Exception as e:
            logger.error(f"Failed to load data sources: {e}")
        finally:
            db.close()

    def _start_oanda(self, config: dict):
        adapter = OandaStreamer(config, self._publish_callback)
        # Default instruments for now, later could be configurable via DB or API
        instruments = ["EUR_USD", "XAU_USD", "GBP_USD", "USD_JPY", "BTC_USD"]
        
        # OANDA v20 expects underscores
        self.adapters['oanda'] = adapter
        # We need to await start, but start is async.
        # Since this is called from async start(), we can await it.
        # But for list iteration, better to gather. 
        # For simplicity in MVP, we iterate.
        import asyncio
        asyncio.create_task(adapter.start(instruments))

    async def _publish_callback(self, data: dict):
        # Channel convention: market_data:{symbol}
        # Symbol format: EUR_USD. 
        symbol = data.get("instrument", "UNKNOWN")
        channel = f"market_data:{symbol}"
        await self.publisher.publish(channel, data)

    async def stop(self):
        logger.info("Stopping StreamManager...")
        for name, adapter in self.adapters.items():
            await adapter.stop()
        await self.publisher.close()

stream_manager = StreamManager()
