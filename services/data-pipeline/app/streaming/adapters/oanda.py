import v20
import threading
import logging
import asyncio
from typing import List, Callable, Awaitable
from app.streaming.adapters.base import StreamAdapter

logger = logging.getLogger(__name__)

class OandaStreamer(StreamAdapter):
    def __init__(self, config: dict, callback: Callable[[dict], Awaitable[None]]):
        super().__init__(callback)
        self.token = config.get("token")
        self.account_id = config.get("account_id")
        self.hostname = config.get("hostname", "stream-fxtrade.oanda.com")
        self.streaming_hostname = config.get("streaming_hostname", self.hostname.replace("api", "stream"))
        
        self._ctx = v20.Context(
            hostname=self.streaming_hostname,
            port=443,
            token=self.token,
            datetime_format="RFC3339"
        )
        self._stop_event = threading.Event()
        self._thread = None
        self._loop = None

    async def start(self, instruments: List[str]):
        if self._thread and self._thread.is_alive():
            logger.warning("OandaStreamer already running")
            return

        formatted_instruments = ",".join([i.replace('/', '_') for i in instruments])
        logger.info(f"Starting OANDA stream for: {formatted_instruments}")
        
        self._stop_event.clear()
        self._loop = asyncio.get_running_loop()
        
        self._thread = threading.Thread(
            target=self._run_stream, 
            args=(formatted_instruments,), 
            daemon=True
        )
        self._thread.start()

    async def stop(self):
        logger.info("Stopping OANDA stream...")
        self._stop_event.set()
        # We don't join/wait here to avoid blocking async loop, 
        # let the thread exit gracefully.

    def _run_stream(self, instruments: str):
        try:
            response = self._ctx.pricing.stream(
                self.account_id,
                instruments=instruments,
                snapshot=True
            )
            
            for msg_type, msg in response.parts():
                if self._stop_event.is_set():
                    break
                    
                if msg_type == "pricing.Price":
                    data = {
                        "type": "PRICE",
                        "source": "oanda",
                        "instrument": msg.instrument,
                        "time": msg.time,
                        "bid": float(msg.bids[0].price),
                        "ask": float(msg.asks[0].price),
                        "status": msg.status
                    }
                    # Init task in the main loop
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(self.callback(data), self._loop)
                        
        except Exception as e:
            logger.error(f"OANDA Stream Error: {e}")
