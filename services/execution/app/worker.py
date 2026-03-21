import asyncio
import json
import logging
import os
import uuid
import redis.asyncio as redis
import time
from datetime import datetime

from app.core.config import settings
from app.core.units import UnitConverter
from app.services.order_service import OrderService
from app.logging_config import setup_logging, set_correlation_id, reset_correlation_id
from app.database import AsyncSessionLocal
from app.services.ai_bridge import AIBridge
from app.adapters.factory import BrokerFactory
from sqlalchemy import select, or_, update
from app.models import Trade, TradeStatus, TradeDirection, BrokerAccount, SignalLog
from app.algorithms.manager import AlgoManager

setup_logging()
logger = logging.getLogger(__name__)

class ExecutionWorker:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        # Priority Queues (Priority > Algo > Default)
        self.queue_names = ["queue:execution:priority", "queue:execution:algo", "queue:execution:commands"]
        self.redis = None
        self._running = False

    async def start(self):
        logger.info(f"Starting Execution Worker, listening on {self.queue_names}...")
        self._running = True
        
        # Start Analytics Snapshot Loop (Parallel task)
        asyncio.create_task(self._analytics_loop())
        # Start Sync Loop (Parallel task)
        asyncio.create_task(self._sync_loop())
        
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
        token = None
        try:
            req_data = json.loads(message_json)
            
            # Setup Correlation Context from client_order_id or request_id
            cid = req_data.get("client_order_id") or req_data.get("request_id")
            if cid:
                token = set_correlation_id(cid)

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
                        # [Latency] Capture Queue Latency
                        enqueued_at = req_data.get("enqueued_at")
                        queue_latency_ms = None
                        if enqueued_at:
                            queue_latency_ms = (time.time() - float(enqueued_at)) * 1000
                            logger.info(f"Queue Latency for {client_order_id or 'unknown'}: {queue_latency_ms:.2f}ms")
                            if self.redis:
                                await self.redis.publish("system.metrics.latency", json.dumps({
                                    "type": "queue_latency",
                                    "symbol": req_data.get("symbol"),
                                    "latency_ms": round(queue_latency_ms, 2),
                                    "client_order_id": client_order_id
                                }))

                        # [Latency] Capture Total E2E Latency
                        signal_ns = req_data.get("signal_timestamp_ns")
                        if signal_ns:
                            total_latency_ms = (time.time_ns() - int(signal_ns)) / 1_000_000
                            logger.info(f"⏱️ TOTAL E2E Latency for {client_order_id or 'unknown'}: {total_latency_ms:.2f}ms")
                            if self.redis:
                                await self.redis.publish("system.metrics.latency", json.dumps({
                                    "type": "e2e_latency",
                                    "symbol": req_data.get("symbol"),
                                    "latency_ms": round(total_latency_ms, 2),
                                    "client_order_id": client_order_id
                                }))

                        if queue_key == "queue:execution:algo":
                            # Process Algorithm Command
                            await AlgoManager.process_algo_step(self.redis, db, req_data)
                            result = {"status": "ALGO_PROCESSED"}
                        else:
                            result = await OrderService.execute_smart_order(req_data, db)
                            
                            # [Latency] Enrich result with latency if available
                            if queue_latency_ms is not None:
                                result["queue_latency_ms"] = round(queue_latency_ms, 2)
                        
                        logger.info(f"Async Execution Success for {req_data.get('symbol')}: {result.get('id') or result.get('status')}")
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
        finally:
            if token:
                reset_correlation_id(token)

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

    async def _analytics_loop(self):
        """
        [INSTITUTIONAL] Background loop to capture account metrics every 15 minutes.
        """
        from app.services.analytics_service import AnalyticsService
        
        logger.info("⏱️ [Analytics] Periodic snapshot loop started.")
        while self._running:
            try:
                await AnalyticsService.capture_all_account_snapshots()
            except Exception as e:
                logger.error(f"⏱️ [Analytics] Loop error: {e}")
            
            # Wait 15 minutes
            await asyncio.sleep(900)

    async def _sync_loop(self):
        """
        [INSTITUTIONAL] Periodic background reconciliation every 30 minutes.
        """
        from app.services.sync_service import SyncService
        
        logger.info("⏱️ [Sync] Periodic reconciliation loop started.")
        while self._running:
            try:
                await SyncService.reconcile_all_funds()
            except Exception as e:
                logger.error(f"⏱️ [Sync] Loop error: {e}")
            
            # Wait 30 minutes
            await asyncio.sleep(1800)


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
            logger.info(f"[FillConsumer] Processing fill data: {data}")

            # Initialize variables to avoid UnboundLocalError
            sl_price = 0.0
            tp_price = 0.0
            
            account_id_str = data.get("account_id", "")
            broker_order_id = data.get("order_id", "")
            symbol = data.get("instrument", "")
            fill_price = float(data.get("fill_price") or data.get("price") or 0.0)
            fill_volume = float(data.get("fill_volume") or data.get("units") or 0.0)
            
            if data.get("sl_price"):
                sl_price = float(data.get("sl_price"))
            if data.get("tp_price"):
                tp_price = float(data.get("tp_price"))

            direction_str = data.get("direction", "LONG")
            comment = data.get("comment", "Manual")

            if not (broker_order_id and symbol):
                logger.warning(f"[FillConsumer] Skipping incomplete fill event: {data}")
                await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
                return

            # [RISK-Calculation] Case-Pro: Use Centralized UnitConverter
            # Standard units = volume_cents / 100.0 (e.g. 10000 -> 100 oz)
            risk_usd = 0.0
            rr_ratio = None
            
            if sl_price and fill_price:
                price_diff = abs(fill_price - sl_price)
                risk_usd = UnitConverter.calculate_risk_usd(price_diff, fill_volume)
                
                if tp_price and price_diff > 0:
                    tp_distance = abs(tp_price - fill_price)
                    rr_ratio = round(tp_distance / price_diff, 2)

            # lot_size for DB (Unified: 1 lot = 100,000 units)
            lot_size = UnitConverter.internal_to_standard_lots(fill_volume)

            from app.services.cache_service import execution_cache
            
            async with AsyncSessionLocal() as db:
                # Resolve BrokerAccount by numeric cTrader account_id (ctid) or account_number
                broker_account_uuid = await execution_cache.get_broker_account_id_by_ctid(account_id_str)
                
                if broker_account_uuid:
                    result = await db.execute(
                        select(BrokerAccount).where(BrokerAccount.id == uuid.UUID(broker_account_uuid))
                    )
                else:
                    # Fallback to account_number (for Oanda/others)
                    result = await db.execute(
                        select(BrokerAccount).where(
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

                direction_str = direction_str.upper()
                if direction_str in ["LONG", "BUY"]:
                    direction = TradeDirection.LONG
                else:
                    direction = TradeDirection.SHORT

                # Check if trade already exists (SyncService might have created it)
                existing_trade = await db.get(Trade, trade_uuid)
                if existing_trade:
                    logger.info(f"[FillConsumer] Reconciling existing ghost trade {trade_uuid} with fill data")
                    existing_trade.status = TradeStatus.OPEN
                    existing_trade.entry_price = fill_price
                    existing_trade.sl_price = sl_price or 0.0
                    existing_trade.tp_price = tp_price or 0.0
                    existing_trade.lot_size = lot_size
                    existing_trade.strategy_name = comment
                    if not existing_trade.metadata_json:
                         existing_trade.metadata_json = {}
                    existing_trade.metadata_json.update({
                        "reconciled": True,
                        "deal_id": data.get("deal_id"),
                        "stream_id": msg_id
                    })
                    new_trade = existing_trade
                else:
                    new_trade = Trade(
                        trade_id=trade_uuid,
                        broker_account_id=broker_account.id,
                        broker_trade_id=str(broker_order_id),
                        broker_deal_id=str(data.get("deal_id")),
                        symbol=symbol,
                        strategy_name=comment,
                        signal_timestamp=datetime.utcnow(),
                        signal_id=uuid.UUID(data.get("trace_id")) if data.get("trace_id") else None,
                        signal_timestamp_ns=data.get("signal_timestamp_ns"),
                        latency_ms=data.get("latency_ms"),
                        is_shadow=data.get("is_shadow", False),
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

                # [SIGNAL-BRIDGE] Synchronize SignalLog status
                if new_trade.signal_id:
                    # Update SignalLog to FILLED and link the new trade_id
                    await db.execute(
                        _update(SignalLog)
                        .where(SignalLog.id == new_trade.signal_id)
                        .values(
                            status="FILLED",
                            execution_id=new_trade.trade_id,
                            filled_price=new_trade.entry_price,
                            filled_time=datetime.utcnow()
                        )
                    )
                
                await db.commit()
            
            # [STATISTICS] Phase 3: Update daily trade count in Redis
            try:
                stats_key = f"account_stats:trades_today:{broker_account.id}"
                await self.redis.incr(stats_key)
                # Set expiry to end of day (approximate)
                await self.redis.expire(stats_key, 86400)
            except Exception as stats_err:
                logger.warning(f"[FillConsumer] Failed to update trades_today stat: {stats_err}")

            # XACK only after successful commit — ensures retry on failure
            await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
            logger.info(
                f"[FillConsumer] ✅ Trade {trade_uuid} persisted and SignalLog {new_trade.signal_id} updated. "
                f"Position {broker_order_id} risk_usd={risk_usd} rr_ratio={rr_ratio}"
            )

            # [AI-FEEDBACK] Phase 6: Trigger Entry Reason Learning (Non-blocking)
            asyncio.create_task(self._trigger_entry_analysis(new_trade))

        except Exception as e:
            logger.error(f"[FillConsumer] Failed to process fill {msg_id}: {e}", exc_info=True)
            # Do NOT XACK — message stays in PEL for retry

    async def _trigger_entry_analysis(self, trade: "Trade"):
        """
        Calls AI Analyst to record reason for entry and updates trade metadata.
        """
        try:
            trade_data = {
                "trade_id": str(trade.trade_id),
                "symbol": trade.symbol,
                "direction": trade.direction,
                "strategy_name": trade.strategy_name,
                "entry_price": trade.entry_price,
                "signal_timestamp_ns": trade.signal_timestamp_ns,
            }
            analysis = await AIBridge.run_entry_analysis(trade_data)
            if analysis:
                async with AsyncSessionLocal() as db:
                    stmt = select(Trade).where(Trade.trade_id == trade.trade_id)
                    res = await db.execute(stmt)
                    t = res.scalar_one_or_none()
                    if t:
                        if not t.metadata_json:
                            t.metadata_json = {}
                        t.metadata_json["entry_analysis"] = analysis
                        await db.commit()
                        logger.info(f"[FillConsumer] AI Entry Analysis saved for {trade.trade_id}")
        except Exception as e:
            logger.error(f"[FillConsumer] AI Entry Analysis failed: {e}")


class CloseTradeConsumer:
    """
    [HFT-Lite] Reads closed trades from Redis Stream `execution.closed.stream`
    Updates real-time statistics in Redis and persists closure to DB.
    """

    STREAM_KEY = "execution.closed.stream"
    GROUP_NAME = "close-trade-writer"
    CONSUMER_NAME = "close-trade-consumer-1"
    BLOCK_MS = 5000

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self._running = False

    async def start(self):
        logger.info(f"[CloseConsumer] Starting, listening on stream '{self.STREAM_KEY}'...")
        self._running = True

        while self._running:
            try:
                if not self.redis:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
                    await self._ensure_consumer_group()

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
                            asyncio.create_task(self._process_close(msg_id, fields))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CloseConsumer] Loop Error: {e}")
                await asyncio.sleep(2)

    async def stop(self):
        self._running = False
        if self.redis:
            await self.redis.close()

    async def _ensure_consumer_group(self):
        try:
            await self.redis.xgroup_create(self.STREAM_KEY, self.GROUP_NAME, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e): raise

    async def _process_close(self, msg_id: str, fields: dict):
        try:
            data = json.loads(fields.get("data", "{}"))
            account_id_str = data.get("account_id")
            deal_id = data.get("deal_id")
            pnl = float(data.get("pnl", 0.0))
            
            from app.services.cache_service import execution_cache
            broker_account_uuid = await execution_cache.get_broker_account_id_by_ctid(account_id_str)
            
            if not broker_account_uuid:
                logger.warning(f"[CloseConsumer] Account mapping not found for {account_id_str}")
                await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
                return

            # 1. Update Real-time Statistics in Redis (Phase 3)
            # Daily PnL
            pnl_key = f"account_stats:daily_pnl:{broker_account_uuid}"
            await self.redis.incrbyfloat(pnl_key, pnl)
            await self.redis.expire(pnl_key, 86400)

            # Consecutive Losses
            loss_key = f"account_stats:consecutive_losses:{broker_account_uuid}"
            if pnl < 0:
                await self.redis.incr(loss_key)
            else:
                await self.redis.set(loss_key, "0")
            await self.redis.expire(loss_key, 86400)

            # 2. Persist to DB
            from app.models import Trade, TradeStatus
            # Removed redundant sqlalchemy import alias
            from datetime import datetime

            async with AsyncSessionLocal() as db:
                # Find the trade by broker_deal_id (cTrader uses dealId for the closure deal)
                # or find by broker_trade_id (positionId)
                # In cTraderAdapter, we use uuid.uuid5(account_id, order_id) where order_id is initial positionId
                # Closures might need reconciliation.
                
                # For now, let's update all OPEN trades for this account and symbol that match the direction?
                # Better: Use a dedicated reconciliation service or look up by broker_trade_id if stored.
                stmt = select(Trade).where(
                    Trade.broker_account_id == uuid.UUID(broker_account_uuid),
                    Trade.status == TradeStatus.OPEN,
                    Trade.symbol == data.get("instrument")
                )
                result = await db.execute(stmt)
                trades = result.scalars().all()
                
                for t in trades:
                    # Simple heuristic: update the first matching open trade
                    # (In production, dealId/positionId mapping is strict)
                    t.status = TradeStatus.CLOSED
                    t.exit_price = float(data.get("exit_price", 0.0))
                    t.exit_timestamp = datetime.utcnow()
                    t.pnl_usd = pnl
                    break
                
                await db.commit()

            await self.redis.xack(self.STREAM_KEY, self.GROUP_NAME, msg_id)
            logger.info(f"[CloseConsumer] ✅ Account {broker_account_uuid} stats updated. PnL: {pnl}")

            # [AI-FEEDBACK] Phase 6: Trigger Post-Mortem Grading (Non-blocking)
            # We use the LAST updated trade for context
            if trades:
                asyncio.create_task(self._trigger_post_mortem(trades[0]))

        except Exception as e:
            logger.error(f"[CloseConsumer] Error: {e}", exc_info=True)

    async def _trigger_post_mortem(self, trade: "Trade"):
        """
        Calls AI Analyst to grade the closed trade and extract lessons.
        """
        try:
            trade_data = {
                "trade_id": str(trade.trade_id),
                "symbol": trade.symbol,
                "direction": trade.direction,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "result_pnl": trade.pnl_usd,
                "strategy_name": trade.strategy_name
            }
            analysis = await AIBridge.run_post_mortem(trade_data)
            if analysis:
                async with AsyncSessionLocal() as db:
                    stmt = select(Trade).where(Trade.trade_id == trade.trade_id)
                    res = await db.execute(stmt)
                    t = res.scalar_one_or_none()
                    if t:
                        if not t.metadata_json:
                            t.metadata_json = {}
                        t.metadata_json["post_mortem"] = analysis
                        await db.commit()
                        logger.info(f"[CloseConsumer] AI Post-Mortem saved for {trade.trade_id}")
        except Exception as e:
            logger.error(f"[CloseConsumer] AI Post-Mortem failed: {e}")


# Global instances
worker = ExecutionWorker()
fill_trade_consumer = FillTradeConsumer()
close_trade_consumer = CloseTradeConsumer()
