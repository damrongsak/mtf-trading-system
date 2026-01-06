import v20
import json
import logging
import asyncio
import time
from app.core.config import settings
from app.streaming.publisher import RedisPublisher

logger = logging.getLogger(__name__)

class TickStreamer:
    def __init__(self):
        self.access_token = settings.OANDA_API_KEY
        self.account_id = settings.OANDA_ACCOUNT_ID
        self.env = settings.OANDA_ENV.lower()
        
        if self.env == "live":
            self.hostname = "stream-fxtrade.oanda.com"
        else:
            self.hostname = "stream-fxpractice.oanda.com"

        self.publisher = RedisPublisher()
        # v20 context for streaming
        # port 443, ssl=True are defaults for Context if not specified? 
        # Check v20 source or assume. The example used create_streaming_context from config.
        # We'll construct manually.
        self.ctx = v20.Context(
            hostname=self.hostname,
            token=self.access_token,
            port=443,
            ssl=True
        )

    async def run(self, instruments: list[str]):
        """
        Connects to OANDA streaming API and publishes ticks to Redis.
        """
        if not instruments:
            logger.warning("No instruments provided for tick streaming.")
            return

        logger.info(f"Starting Tick Streamer for {instruments} on {self.hostname}")
        
        await self.publisher.connect()
        queue = asyncio.Queue()
        
        loop = asyncio.get_running_loop()
        # Run the blocking stream listener in a separate thread
        # We keep a reference to the future but we don't await it directly
        # because it runs forever. We await the consumer loop.
        # We can use run_in_executor.
        
        worker_future = loop.run_in_executor(None, self._stream_worker, instruments, loop, queue)
        
        try:
            while True:
                msg = await queue.get()
                if msg is None: # Error sentinel
                    break
                
                # Publish to Redis
                # Pattern: market_data:tick:{symbol}
                channel = f"market_data:tick:{msg['instrument']}"
                try:
                    await self.publisher.publish(channel, msg)
                except Exception as pub_err:
                    logger.error(f"Publish error: {pub_err}")
                
                queue.task_done()
        except asyncio.CancelledError:
            logger.info("TickStreamer cancelled.")
        except Exception as e:
            logger.error(f"TickStreamer consumer error: {e}")
        finally:
            await self.publisher.close()

    def _stream_worker(self, instruments, loop, queue):
        """
        Blocking worker to fetch stream data.
        """
        inst_str = ",".join(instruments)
        
        while True:
            try:
                logger.info(f"Connecting to OANDA stream for: {inst_str}")
                response = self.ctx.pricing.stream(
                    self.account_id,
                    snapshot=True,
                    instruments=inst_str
                )
                
                # response.parts() is a generator that blocks waiting for chunks
                for msg_type, msg in response.parts():
                    logger.debug(f"Received msg type: {msg_type}")
                    if msg_type == "pricing.Price" or msg_type == "pricing.ClientPrice":
                        # Construct payload
                        # msg is a Model instance, access fields directly
                        payload = {
                            "type": "tick",
                            "instrument": msg.instrument,
                            "time": msg.time,
                            "bid": float(msg.bids[0].price) if msg.bids else None,
                            "ask": float(msg.asks[0].price) if msg.asks else None,
                            "status": msg.status
                            # Could add liquidity/volume if needed
                        }
                        
                        # Send to async loop
                        asyncio.run_coroutine_threadsafe(queue.put(payload), loop)
                        
                    elif msg_type == "pricing.Heartbeat" or msg_type == "pricing.PricingHeartbeat":
                        # Optional: Health check logic
                        pass
                        
            except Exception as e:
                logger.error(f"OANDA Stream disconnected/error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                time.sleep(5)
