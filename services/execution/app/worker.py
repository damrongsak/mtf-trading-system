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
        # Priority Queues (Priority > Default)
        self.queue_names = ["queue:execution:priority", "queue:execution:commands"]
        self.redis = None
        self._running = False

    async def start(self):
        logger.info(f"Starting Execution Worker, listening on {self.queue_names}...")
        self._running = True
        
        while self._running:
            try:
                if not self.redis:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
                
                # BRPOP returns (queue_name, message) - Multi-key prioritizes strictly from left to right
                result = await self.redis.brpop(self.queue_names, timeout=5)
                if result:
                    queue_key, message_json = result
                    logger.info(f"Received from {queue_key}: {message_json}")
                    # Process in a separate task to avoid blocking the queue consumer
                    asyncio.create_task(self._process_command(queue_key, message_json))
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

    async def _process_command(self, queue_key: str, message_json: str):
        try:
            req_data = json.loads(message_json)
            
            # 0. Global Kill Switch Check
            if self.redis:
                is_halted = await self.redis.get("system:kill_switch") == "1"
                if is_halted:
                    cmd_type = req_data.get("type", "OPEN").upper()
                    # Emergency: Allow Close/Modify to bypass halt? 
                    # Plan says: "reject all new trade commands". 
                    # Let's reject OPEN but maybe log warning for others.
                    if cmd_type == "OPEN":
                        logger.warning(f"🛑 SYSTEM HALTED: Rejecting OPEN command for {req_data.get('symbol')}")
                        return
                    else:
                        logger.info(f"⚠️ SYSTEM HALTED: Processing priority command {cmd_type} despite halt.")
            
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
                    # Release lock so it can be retried
                    if client_order_id and self.redis:
                        await self.redis.delete(f"processed_order:{client_order_id}")
                    await self._handle_error(queue_key, req_data, str(biz_e))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received in queue: {message_json}")
        except Exception as e:
            logger.error(f"Unexpected error in _process_command: {e}", exc_info=True)

    async def _handle_error(self, origin_queue: str, req_data: dict, error_msg: str):
        if not self.redis:
            return
            
        retry_count = req_data.get("retry_count", 0)
        client_order_id = req_data.get("client_order_id", "unknown")
        
        if retry_count < 3:
            req_data["retry_count"] = retry_count + 1
            req_data["last_error"] = error_msg
            logger.warning(f"⏳ Retrying order {client_order_id} ({retry_count+1}/3) in queue {origin_queue}")
            # Push back to the end of the same queue
            await self.redis.lpush(origin_queue, json.dumps(req_data))
        else:
            logger.error(f"☠️ DEAD LETTER: Order {client_order_id} failed after 3 retries. Moving to DLQ.")
            req_data["last_error"] = error_msg
            await self.redis.lpush("queue:exec:dead", json.dumps(req_data))

# Global instance for easy starting
worker = ExecutionWorker()
