import v20
import asyncio
import json
import logging
import threading
from typing import List, AsyncGenerator, Set
from app.database import SessionLocal
from sqlalchemy import func
from app.models.data_source import DataSource

# Configure logging
logger = logging.getLogger(__name__)

class PriceStreamer:
    def __init__(self):
        self._ctx = None
        self._account_id = None
        self._configured = False
        self._subscribers: Set[asyncio.Queue] = set()
        self._is_streaming = False
        self._stop_event = None
        self._stream_thread = None
        self._active_instruments: Set[str] = set()

    def _configure(self):
        """
        Load configuration from Database (DataSource table).
        """
        logger.info("Entering _configure")
        if self._configured:
            return

        db = SessionLocal()
        try:
            logger.info("Querying DataSource for 'oanda'...")
            ds = db.query(DataSource).filter(func.lower(DataSource.name) == 'oanda').first()
            if not ds:
                logger.warning("No 'oanda' DataSource found in DB.")
                return

            config = ds.config_json
            token = config.get("token")
            hostname = config.get("hostname", "stream-fxtrade.oanda.com")
            
            streaming_hostname = config.get("streaming_hostname", hostname.replace("api", "stream"))
            logger.info(f"Using Streaming Hostname: {streaming_hostname}")

            self._ctx = v20.Context(
                hostname=streaming_hostname,
                port=443,
                token=token,
                datetime_format="RFC3339"
            )
            self._account_id = config.get("account_id")
            self._configured = True
            logger.info(f"PriceStreamer configured for account {self._account_id}")

        except Exception as e:
            logger.error(f"Failed to configure PriceStreamer: {e}")
        finally:
            db.close()

    async def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to price updates. Returns an asyncio.Queue.
        """
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def _broadcast(self, data: dict):
        for queue in list(self._subscribers):
            try:
                # Use put_nowait to avoid blocking if a consumer is slow
                # If full, we might drop frames or block? 
                # For prices, dropping old frames is better than blocking, 
                # but asyncio.Queue is unbounded by default.
                queue.put_nowait(data)
            except Exception as e:
                logger.error(f"Error broadcasting to subscriber: {e}")
                self.unsubscribe(queue)

    def start_streaming(self, instruments: List[str]):
        """
        Start the background stream thread if not already running.
        Update active instruments if needed (requires restart of stream usually).
        """
        self._configure()
        if not self._ctx or not self._account_id:
            logger.error("PriceStreamer not configured, cannot start.")
            return

        new_instruments = set(instruments)
        if self._is_streaming:
            if new_instruments.issubset(self._active_instruments):
                 # Already covering these instruments
                 return
            else:
                # Need to restart with expanded list? 
                # For simplicity in MVP, we might just restart or union.
                # Let's union and restart.
                self._active_instruments.update(new_instruments)
                self.stop_streaming()
                # Fallthrough to start
        else:
             self._active_instruments = new_instruments

        logger.info(f"Starting OANDA stream for {self._active_instruments}")
        self._stop_event = threading.Event()
        self._is_streaming = True
        
        loop = asyncio.get_event_loop()

        def run_stream():
            try:
                inst_list = ",".join([i.replace('/', '_') for i in self._active_instruments])
                response = self._ctx.pricing.stream(
                    self._account_id,
                    instruments=inst_list,
                    snapshot=True
                )
                for msg_type, msg in response.parts():
                    if self._stop_event.is_set():
                        break
                        
                    if msg_type == "pricing.Heartbeat":
                        continue
                        
                    if msg_type == "pricing.Price":
                        # Convert v20 object to dict
                        data = {
                            "type": "PRICE",
                            "instrument": msg.instrument,
                            "time": msg.time,
                            "bid": float(msg.bids[0].price),
                            "ask": float(msg.asks[0].price),
                            "status": msg.status
                        }
                        # Threadsafe broadcast
                        asyncio.run_coroutine_threadsafe(self._broadcast(data), loop)
            except Exception as e:
                logger.error(f"Stream thread error: {e}")
                asyncio.run_coroutine_threadsafe(
                    self._broadcast({"type": "ERROR", "msg": str(e)}), loop
                )
            finally:
                logger.info("OANDA stream thread exited")
                self._is_streaming = False

        self._stream_thread = threading.Thread(target=run_stream, daemon=True)
        self._stream_thread.start()

    def stop_streaming(self):
        if self._is_streaming and self._stop_event:
            self._stop_event.set()
            # We can't join here if called from async loop, but daemon thread will die eventually
            self._is_streaming = False
            logger.info("Stop signal sent to stream thread")

    async def stream(self, instruments: List[str]) -> AsyncGenerator[dict, None]:
        """
        Legacy/WebSocket compatible generator.
        Manages its own subscription.
        """
        self.start_streaming(instruments)
        queue = await self.subscribe()
        try:
            while True:
                data = await queue.get()
                yield data
        finally:
            self.unsubscribe(queue)

price_streamer = PriceStreamer()

