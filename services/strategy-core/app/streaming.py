import v20
import asyncio
import json
import logging
from typing import List, AsyncGenerator
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

    def _configure(self):
        """
        Load configuration from Database (DataSource table).
        Assumes there is an 'oanda' data source.
        """
        logger.info("Entering _configure")
        if self._configured:
            logger.info("PriceStreamer already configured")
            return

        db = SessionLocal()
        try:
            # For now, hardcode looking for 'oanda' or taking the first one
            # Query by name instead of ID (which is UUID)
            logger.info("Querying DataSource for 'oanda'...")
            ds = db.query(DataSource).filter(func.lower(DataSource.name) == 'oanda').first()
            if not ds:
                # Fallback to env vars or raise error
                logger.warning("No 'oanda' DataSource found in DB.")
                # You might want to implement env var fallback here
                return

            config = ds.config_json
            token = config.get("token")
            hostname = config.get("hostname", "stream-fxtrade.oanda.com")
            logger.info(f"Loaded config. Hostname: {hostname}")
            
            # Note: Streaming usually uses a different hostname (stream-fxpractice or stream-fxtrade)
            # The OandaAdapter might use api-fxpractice. We need to ensure we use the STREAMING url.
            # v20 Context might handle this if properly configured, or we pass hostname.
            
            # Allow override for streaming specifically
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

    async def stream(self, instruments: List[str]) -> AsyncGenerator[dict, None]:
        """
        Connect to OANDA stream and yield price updates.
        """
        self._configure()
        if not self._ctx or not self._account_id:
            logger.error("PriceStreamer not configured.")
            # Yield a mock or heartbeat if configured fails, or just stop
            return

        logger.info(f"Starting stream for {instruments}")
        
        # OANDA v20 streaming is synchronous/blocking in some implementations or requires threading.
        # However, we are in asyncio. 
        # The v20 sample uses `response.parts()` which is a generator.
        # We need to run the stream request in an executor/thread to not block the event loop,
        # OR use a non-blocking request style. 
        
        # Since v20 library is synchronous, we'll wrap the iteration in a way that doesn't block entirely,
        # but realistically, keeping a long-lived sync request open in an async handler is tricky.
        # A better approach for fully async is using `aiohttp` directly to call the OANDA stream endpoint.
        # But let's try to stick to v20 if possible or wrap it.
        
        # Actually, for robustness in this tech stack, implementing a direct async streamer 
        # might be cleaner than wrestling with the synchronous v20 library inside FastAPI async.
        # Let's write a simple async streamer using httpx/aiohttp principles but kept simple here.
        # OR: Run the v20 stream in a separate thread and push to an asyncio.Queue.
        
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        stop_event = asyncio.Event()

        def run_stream():
            try:
                response = self._ctx.pricing.stream(
                    self._account_id,
                    instruments=",".join([i.replace('/', '_') for i in instruments]),
                    snapshot=True
                )
                for msg_type, msg in response.parts():
                    if stop_event.is_set():
                        break
                        
                    if msg_type == "pricing.Heartbeat":
                        continue
                        
                    if msg_type == "pricing.Price":
                        # Convert v20 object to dict
                        data = {
                            "type": "PRICE",
                            "instrument": msg.instrument,
                            "time": msg.time,
                            "bid": float(msg.bids[0].price), # Top of book
                            "ask": float(msg.asks[0].price), # Top of book
                            "status": msg.status
                        }
                        # Threadsafe put
                        # logger.info(f"OANDA Stream: Received {data['instrument']}") 
                        asyncio.run_coroutine_threadsafe(queue.put(data), loop)
            except Exception as e:
                logger.error(f"Stream error: {e}")
                asyncio.run_coroutine_threadsafe(queue.put({"type": "ERROR", "msg": str(e)}), loop)

        # Start stream in separate thread
        import threading
        stream_thread = threading.Thread(target=run_stream, daemon=True)
        stream_thread.start()

        try:
            while True:
                data = await queue.get()
                if data.get("type") == "ERROR":
                    logger.error(f"Stream received error: {data['msg']}")
                    break
                logger.info(f"Yielding price: {data.get('instrument')}")
                yield data
        except asyncio.CancelledError:
            logger.info("Stream cancelled")
            stop_event.set()
        finally:
            stop_event.set()
            # We can't easily kill the thread blocked on socket read without closing socket.
            # v20 context doesn't expose easy abort. Ideally, we just let it die or restart.

price_streamer = PriceStreamer()
