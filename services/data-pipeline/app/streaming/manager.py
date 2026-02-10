from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.streaming.adapters.oanda import OandaStreamer
from app.streaming.adapters.ctrader import CTraderStreamer
from app.streaming.publisher import RedisPublisher
from app.repositories.market_repository import MarketRepository
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
            repo = MarketRepository(db)
            data_sources = repo.get_active_data_sources()
            logger.info(f"Found {len(data_sources)} active data sources")
            
            for ds in data_sources:
                # Fetch symbols configured for this data source
                symbols = repo.get_symbols_for_datasource(ds.id)
                
                symbol_list = [s.symbol for s in symbols]
                
                if not symbol_list:
                    logger.warning(f"No symbols found for data source {ds.name}")
                    continue

                if ds.provider == 'OANDA':
                    self._start_oanda(ds.config_json, symbol_list)
                elif ds.provider == 'CTRADER':
                    self._start_ctrader(ds.config_json, symbol_list)
                
        except Exception as e:
            logger.error(f"Failed to load data sources: {e}")
        finally:
            db.close()

    def _start_oanda(self, config: dict, instruments: list):
        adapter = OandaStreamer(config, self._publish_callback)
        self.adapters['oanda'] = adapter
        import asyncio
        asyncio.create_task(adapter.start(instruments))

    def _start_ctrader(self, config: dict, instruments: list):
        adapter = CTraderStreamer(config, self._publish_callback)
        self.adapters['ctrader'] = adapter
        import asyncio
        asyncio.create_task(adapter.start(instruments))

    async def _publish_callback(self, data: dict):
        # Channel convention: market_data:{type}:{symbol}
        event_type = data.get("type", "tick").lower()
        symbol = data.get("instrument", "UNKNOWN")
        
        if event_type == "symbol_details":
            channel = f"market_data:info:{symbol}"
        else:
            channel = f"market_data:tick:{symbol}"
            
        await self.publisher.publish(channel, data)

    async def refresh_subscriptions(self):
        """
        Re-reads the database and restarts streaming with updated symbol list.
        Useful when new symbols are added to the system dynamically.
        """
        logger.info("Refreshing subscriptions...")
        # Stop existing adapters
        for name, adapter in self.adapters.items():
            await adapter.stop()
        
        self.adapters = {}
        # Restart (will re-query DB)
        # Note: We skip re-connecting publisher as it stays open
        # But start() calls publisher.connect(). create idempotency check in publisher or here.
        
        # Load configs logic duplicated? No, start() has it. 
        # But start() connects publisher first.
        # Let's extract load_logic or just ensure publisher.connect() is safe to call twice.
        
        # For simplicity in this implementation, we just call start() again. 
        # RedisPublisher.connect should be idempotent.
        await self.start()

    async def stop(self):
        logger.info("Stopping StreamManager...")
        for name, adapter in self.adapters.items():
            await adapter.stop()
        await self.publisher.close()

stream_manager = StreamManager()
