from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.data_source import DataSource
from app.models.market import MarketSymbol
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
                # Fetch symbols configured for this data source
                symbols = db.query(MarketSymbol).filter(
                    MarketSymbol.data_source_id == ds.id
                ).all()
                
                symbol_list = [s.symbol for s in symbols]
                
                if not symbol_list:
                    logger.warning(f"No symbols found for data source {ds.name}")
                    continue

                if ds.name.lower() == 'oanda':
                    self._start_oanda(ds.config_json, symbol_list)
                # Add other adapters here (e.g. Binance)
                
        except Exception as e:
            logger.error(f"Failed to load data sources: {e}")
        finally:
            db.close()

    def _start_oanda(self, config: dict, instruments: list):
        adapter = OandaStreamer(config, self._publish_callback)
        
        # OANDA v20 expects underscores
        self.adapters['oanda'] = adapter
        
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
