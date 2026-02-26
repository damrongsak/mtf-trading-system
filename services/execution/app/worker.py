import asyncio
import json
import logging
import os
import redis.asyncio as redis
from app.database import AsyncSessionLocal
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

class ExecutionWorker:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.queue_name = "queue:execution:commands"
        self.redis = None
        self._running = False

    async def start(self):
        logger.info(f"Starting Execution Worker, listening on {self.queue_name}...")
        self._running = True
        
        while self._running:
            try:
                if not self.redis:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
                
                # BRPOP returns (key, message)
                result = await self.redis.brpop(self.queue_name, timeout=5)
                if result:
                    _, message_json = result
                    logger.info(f"Received command: {message_json}")
                    # Process in a separate task to avoid blocking the queue consumer
                    asyncio.create_task(self._process_command(message_json))
            except asyncio.CancelledError:
                break
            except redis.ConnectionError as ce:
                logger.error(f"Redis Connection Error: {ce}. Retrying in 5s...")
                self.redis = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        if self.redis:
            await self.redis.close()
        logger.info("Execution Worker stopped.")

    async def _process_command(self, message_json: str):
        try:
            req_data = json.loads(message_json)
            
            # 1. Idempotency Check (SETNX)
            client_order_id = req_data.get("client_order_id")
            if client_order_id and self.redis:
                idempotency_key = f"processed_order:{client_order_id}"
                # nx=True means "Set if Not eXists", ex=86400 means 24 hours TTL
                is_new = await self.redis.set(idempotency_key, "1", ex=86400, nx=True)
                if not is_new:
                    logger.warning(f"🚨 Idempotency Reject: Order {client_order_id} already processed. Dropping duplicate message from queue.")
                    return
            
            # 2. Process Command
            async with AsyncSessionLocal() as db:
                try:
                    command_type = req_data.get("type", "order")
                    if command_type == "update_quotes":
                        result = await OrderService.update_market_quotes(req_data, db)
                        logger.info(f"Quote Update Success for {req_data.get('symbol')}")
                    else:
                        result = await OrderService.execute_smart_order(req_data, db)
                        logger.info(f"Async Execution Success for {req_data.get('symbol')}: {result.get('id')}")
                except Exception as biz_e:
                    logger.error(f"Async Execution Biz Logic Error: {biz_e}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received in queue: {message_json}")
        except Exception as e:
            logger.error(f"Unexpected error in _process_command: {e}", exc_info=True)

# Global instance for easy starting
worker = ExecutionWorker()
