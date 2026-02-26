import asyncio
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.signal_log import SignalLog
from app.streaming.subscriber import RedisSubscriber
from app.engine.core import strategy_engine # for notifications

logger = logging.getLogger(__name__)

class ReconciliationWorker:
    def __init__(self):
        self.subscriber = RedisSubscriber(self.on_execution_event)
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info("Starting Reconciliation Worker (Watchdog & Event Listener)...")
        # Start the subscriber
        await self.subscriber.connect()
        await self.subscriber.subscribe(["execution:events"])
        # Start the watchdog
        asyncio.create_task(self.watchdog_loop())

    async def stop(self):
        self.is_running = False
        await self.subscriber.stop()

    async def on_execution_event(self, channel: str, data: dict):
        """
        Handle incoming events from the Gateway.
        Expected format: {"order_id": "UUID", "status": "FILLED"|"REJECTED", "price": 2030.5}
        """
        try:
            order_id = data.get("order_id")
            status = data.get("status")
            price = data.get("price")
            
            if not order_id or not status:
                return

            db = SessionLocal()
            try:
                # order_id matches SignalLog.id (UUID string)
                signal = db.query(SignalLog).filter(SignalLog.id == order_id).first()
                if signal:
                    signal.status = status
                    if price:
                        signal.price = price
                    db.commit()
                    logger.info(f"Reverse Event: Order {order_id} updated to {status}")
            except Exception as e:
                logger.error(f"Error updating signal log from event: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error handling execution event: {e}")

    async def watchdog_loop(self):
        """
        Periodically checks for PENDING orders that have timed out.
        """
        while self.is_running:
            try:
                db = SessionLocal()
                # 10 seconds timeout
                timeout_threshold = datetime.utcnow() - timedelta(seconds=10)
                
                orphaned_orders = db.query(SignalLog).filter(
                    SignalLog.status == "PENDING",
                    SignalLog.timestamp < timeout_threshold
                ).all()

                for order in orphaned_orders:
                    order.status = "TIMEOUT"
                    db.commit()
                    msg = f"🚨 Watchdog Alert: Order {order.id} ({order.symbol} {order.direction}) stuck in PENDING > 10s. Marked as TIMEOUT."
                    logger.warning(msg)
                    # Notify system plugins (Telegram etc)
                    strategy_engine.notify(msg, category="alert")
                
                db.close()
            except Exception as e:
                logger.error(f"Error in reconciliation watchdog: {e}")
                
            await asyncio.sleep(5) # Run every 5 seconds

reconciliation_worker = ReconciliationWorker()
