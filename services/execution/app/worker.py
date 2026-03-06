import asyncio
import json
import logging
import os
import uuid
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


# ─────────────────────────────────────────────────────────────────────────────
# FillTradeConsumer — HFT-Lite Compliant DB persistence
# ─────────────────────────────────────────────────────────────────────────────

class FillTradeConsumer:
    """
    [HFT-Lite] Reads filled orders from Redis Stream `execution.filled.stream`
    and persists them as Trade records to PostgreSQL.

    This keeps the hot execution path completely DB-free.
    Uses XREADGROUP for exactly-once delivery with XACK.
    """

    STREAM_KEY = "execution.filled.stream"
    GROUP_NAME = "fill-trade-writer"
    CONSUMER_NAME = "fill-trade-consumer-1"
    BLOCK_MS = 5000  # Block for 5s waiting for new messages

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self._running = False

    async def start(self):
        logger.info(f"[FillConsumer] Starting, listening on stream '{self.STREAM_KEY}'...")
        self._running = True

        while self._running:
            try:
                if not self.redis:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
                    await self._ensure_consumer_group()

                # XREADGROUP — block waiting for new messages
                results = await self.redis.xreadgroup(
                    groupname=self.GROUP_NAME,
                    consumername=self.CONSUMER_NAME,
                    streams={self.STREAM_KEY: ">"},
                    count=10,
                    block=self.BLOCK_MS,
                )

                if results:
                    for _stream_name, messages in results:
                        for msg_id, fields in messages:
                            asyncio.create_task(self._process_fill(msg_id, fields))

            except asyncio.CancelledError:
                break
            except redis.ConnectionError as ce:
                logger.error(f"[FillConsumer] Redis Connection Error: {ce}. Retrying in 5s...")
                self.redis = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[FillConsumer] Loop Error: {e}", exc_info=True)
                await asyncio.sleep(2)

    async def stop(self):
        self._running = False
        if self.redis:
            await self.redis.close()
        logger.info("[FillConsumer] Stopped.")

    async def _ensure_consumer_group(self):
        """Create consumer group if it doesn't already exist."""
        try:
            await self.redis.xgroup_create(
                self.STREAM_KEY, self.GROUP_NAME, id="0", mkstream=True
            )
            logger.info(f"[FillConsumer] Consumer group '{self.GROUP_NAME}' created.")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                pass  # Group already exists — expected on restart
            else:
                raise

    async def _process_fill(self, msg_id: str, fields: dict):
        """
        Deserialize fill event and persist Trade to DB.
        Computes risk_usd and rr_ratio from fill data.
        ACKs the message only after successful DB commit.
        """
        try:
            data = json.loads(fields.get("data", "{}"))

            account_id_str = data.get("account_id", "")
            broker_order_id = data.get("order_id", "")
            symbol = data.get("instrument", "")
            fill_price = float(data.get("fill_price", 0.0))
            fill_volume = float(data.get("fill_volume", 0.0))
            sl_price = float(data.get("sl_price", 0.0))
            tp_price = float(data.get("tp_price", 0.0))
            direction_str = data.get("direction", "LONG")
            comment = data.get("comment", "Manual")

            if not (broker_order_id and symbol):
                logger.warning(f"[FillConsumer] Skipping incomplete fill event: {data}")
                await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
                return

            # Compute derived fields
            risk_usd = 0.0
            rr_ratio = None
            lot_size = abs(fill_volume) / 100000.0

            if sl_price and fill_price:
                sl_distance = abs(fill_price - sl_price)
                # Simplified: risk per pip × distance (xauusd: 1 pip ≈ $1 per 0.01 lot)
                risk_usd = round(sl_distance * lot_size * 100, 2)

                if tp_price and sl_distance > 0:
                    tp_distance = abs(tp_price - fill_price)
                    rr_ratio = round(tp_distance / sl_distance, 2)

            from app.models import Trade, TradeStatus, TradeDirection, BrokerAccount
            from sqlalchemy import select as _select
            from datetime import datetime

            async with AsyncSessionLocal() as db:
                # Resolve BrokerAccount by numeric cTrader account_id
                result = await db.execute(
                    _select(BrokerAccount).where(
                        BrokerAccount.account_number == account_id_str
                    )
                )
                broker_account = result.scalars().first()

                if not broker_account:
                    logger.warning(
                        f"[FillConsumer] BrokerAccount not found for account_id={account_id_str}. "
                        "Skipping DB save."
                    )
                    await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
                    return

                # Deterministic UUID — prevents duplicates on replay
                trade_uuid = uuid.uuid5(
                    uuid.NAMESPACE_DNS, f"{str(broker_account.id)}_{broker_order_id}"
                )

                direction = TradeDirection.LONG if direction_str == "LONG" else TradeDirection.SHORT

                new_trade = Trade(
                    trade_id=trade_uuid,
                    broker_account_id=broker_account.id,
                    broker_trade_id=str(broker_order_id),
                    symbol=symbol,
                    strategy_name=comment,
                    signal_timestamp=datetime.utcnow(),
                    status=TradeStatus.OPEN,
                    direction=direction,
                    entry_price=fill_price,
                    exit_price=None,
                    sl_price=sl_price or 0.0,
                    tp_price=tp_price or 0.0,
                    lot_size=lot_size,
                    risk_usd=risk_usd,
                    rr_ratio=rr_ratio,
                    pnl_usd=0.0,
                    exit_timestamp=None,
                    metadata_json={
                        "broker_position_id": broker_order_id,
                        "deal_id": data.get("deal_id"),
                        "stream_msg_id": msg_id,
                    },
                )
                await db.merge(new_trade)
                await db.commit()

            # XACK only after successful commit — ensures retry on failure
            await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
            logger.info(
                f"[FillConsumer] ✅ Trade {trade_uuid} persisted for position {broker_order_id} "
                f"risk_usd={risk_usd} rr_ratio={rr_ratio}"
            )

        except Exception as e:
            logger.error(f"[FillConsumer] Failed to process fill {msg_id}: {e}", exc_info=True)
            # Do NOT XACK — message stays in PEL for retry


# Global instances
worker = ExecutionWorker()
fill_trade_consumer = FillTradeConsumer()
