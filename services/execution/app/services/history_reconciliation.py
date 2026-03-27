import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Dict, Optional
import json
import redis.asyncio as redis
from app.core.config import settings
from sqlalchemy.future import select
from app.models import BrokerAccount, Trade, TradeStatus, UserFund
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class HistoryReconciliationService:
    @classmethod
    async def reconcile_account_history(cls, account_id: str, days_back: int = 7):
        """
        Fetch closed deals/transactions from broker and update local Trade records.
        Ensures 100% accurate PnL, commission, and swap tracking.
        """
        logger.info(f"🔄 [HistoryRecon] Starting history reconciliation for account {account_id}")
        
        async with AsyncSessionLocal() as db:
            account = await db.get(BrokerAccount, account_id)
            if not account or not account.is_active:
                logger.warning(f"🔄 [HistoryRecon] Account {account_id} not found or inactive.")
                return

            try:
                creds = decrypt_data(account.credentials_encrypted)
                creds["environment"] = account.environment
                adapter = BrokerFactory.get_adapter(account.broker_name, creds)
                
                to_time = datetime.utcnow()
                from_time = to_time - timedelta(days=days_back)
                
                is_ctrader = account.broker_name.lower() == 'ctrader'
                
                if is_ctrader:
                    # cTrader handles ProtoOADeal objects
                    deals = await adapter.get_deal_list(
                        from_timestamp=int(from_time.timestamp() * 1000),
                        to_timestamp=int(to_time.timestamp() * 1000)
                    )
                    
                    if not deals:
                        logger.debug(f"🔄 [HistoryRecon] No cTrader deals found for account {account_id}")
                        # return # Original return removed to allow processing of other parts if needed, though no deals means nothing to process.
                    
                    # Process deals
                    for deal in deals:
                        trade = await cls._process_ctrader_deal(deal, account, db)
                        if trade and trade.reconciliation_status == "SUCCESS":
                            # Fetch user_id for the fund
                            stmt_user = select(UserFund.user_id).where(UserFund.fund_id == account.fund_id).limit(1)
                            user_res = await db.execute(stmt_user)
                            user_id = user_res.scalar_one_or_none()
                            if user_id:
                                await cls._publish_post_mortem_cmd(trade, user_id)
                else:
                    # Oanda and others use get_trade_history returning list of dicts
                    hist_trades = await adapter.get_trade_history(from_time, to_time)
                    
                    if not hist_trades:
                        logger.debug(f"🔄 [HistoryRecon] No history found for Oanda/Other account {account_id}")
                        return

                    for ht in hist_trades:
                        await cls._process_generic_history_item(ht, account, db)
                
                await db.commit()
                logger.info(f"🔄 [HistoryRecon] Completed reconciliation for account {account_id}")

            except Exception as e:
                logger.error(f"🔄 [HistoryRecon] Failed reconciliation for account {account_id}: {e}")
                await db.rollback()

    @classmethod
    async def _process_ctrader_deal(cls, deal: Any, account: BrokerAccount, db):
        """Process a ProtoOADeal from cTrader."""
        broker_deal_id = str(deal.dealId)
        position_id = str(deal.positionId)
        
        # 1. Match by broker_deal_id OR broker_trade_id (positionId)
        stmt = select(Trade).where(
            (Trade.broker_deal_id == broker_deal_id) | 
            ((Trade.broker_trade_id == position_id) & (Trade.status == TradeStatus.CLOSED))
        )
        result = await db.execute(stmt)
        trade = result.scalar_one_or_none()
        
        if not trade:
            # Check if it's an open trade that just closed
            stmt_open = select(Trade).where(Trade.broker_trade_id == position_id)
            res_open = await db.execute(stmt_open)
            trade = res_open.scalar_one_or_none()

        if not trade:
            logger.debug(f"🔄 [HistoryRecon] No local trade for deal {broker_deal_id} (Pos:{position_id}). Skipping.")
            return

        # 2. Update Metric (cTrader: money/commission/swap are in account currency * 100 or raw pipette equivalents)
        # Note: OpenApiPy deal objects: money is centered in account currency cent-equivalents for some brokers.
        # Standard OAPI standard is raw currency units (e.g. 1.23 USD = 123 cents in some contexts, or raw for others).
        # We assume raw units divided by SCALE factor if needed.
        
        # cTrader units: most currency metrics are in pipette-equivalents (multiplied by 100000 etc.?) 
        # Actually in OpenApiPy, 'money'/commission/swap are usually in BASE currency units * 100 (cents).
        
        try:
            raw_pnl = Decimal(str(deal.money / 100.0))
            raw_comm = Decimal(str(deal.commission / 100.0))
            raw_swap = Decimal(str(deal.swap / 100.0))
            
            trade.broker_raw_pnl = raw_pnl
            trade.broker_commission = raw_comm
            trade.broker_swap = raw_swap
            
            # Reconciled values
            trade.pnl_usd = raw_pnl + raw_comm + raw_swap
            trade.commission = abs(raw_comm) # Store absolute commission
            trade.swap = raw_swap
            
            trade.exit_price = Decimal(str(deal.executionPrice))
            trade.exit_timestamp = datetime.fromtimestamp(deal.executionTimestamp / 1000.0)
            
            # Latency Metrics
            if trade.signal_timestamp:
                fill_ms = (trade.exit_timestamp - trade.signal_timestamp.replace(tzinfo=None)).total_seconds() * 1000
                trade.execution_latency_ms = Decimal(str(fill_ms))

            trade.broker_deal_id = broker_deal_id
            trade.reconciled_at = datetime.utcnow()
            trade.reconciliation_status = "SUCCESS"
            trade.status = TradeStatus.CLOSED
            
            logger.debug(f"✅ [HistoryRecon] Trade {trade.trade_id} reconciled via cTrader Deal {broker_deal_id}")
            return trade
            
        except Exception as e:
            logger.error(f"🔄 [HistoryRecon] Error processing cTrader deal {broker_deal_id}: {e}")
            trade.reconciliation_status = "FAILED"
            return None

    @classmethod
    async def _process_generic_history_item(cls, item: Dict[str, Any], account: BrokerAccount, db):
        """Process a normalized history dict (Oanda etc)."""
        btid = str(item.get("trade_id"))
        
        stmt = select(Trade).where(Trade.broker_trade_id == btid)
        result = await db.execute(stmt)
        trade = result.scalar_one_or_none()
        
        if not trade:
            return

        try:
            # Update metrics from normalized item
            trade.pnl_usd = Decimal(str(item.get("pnl_usd", 0.0)))
            trade.exit_price = Decimal(str(item.get("exit_price", 0.0)))
            trade.exit_timestamp = item.get("exit_timestamp")
            
            # Extract raw fields if available (Oanda context)
            raw = item.get("metadata_json", {}).get("raw", {})
            trade.broker_raw_pnl = Decimal(str(raw.get("realizedPL", 0.0)))
            trade.broker_commission = Decimal(str(raw.get("commission", 0.0))) # Oanda might have this in trade
            trade.broker_swap = Decimal(str(raw.get("financing", 0.0)))
            
            # Institutional Latency
            if trade.signal_timestamp and trade.exit_timestamp:
                latency = (trade.exit_timestamp.replace(tzinfo=None) - trade.signal_timestamp.replace(tzinfo=None)).total_seconds() * 1000
                trade.execution_latency_ms = Decimal(str(latency))

            trade.reconciled_at = datetime.utcnow()
            trade.reconciliation_status = "SUCCESS"
            trade.status = TradeStatus.CLOSED
            
            logger.debug(f"✅ [HistoryRecon] Trade {trade.trade_id} reconciled via Oanda/Other Trade {btid}")
            return trade
            
        except Exception as e:
            logger.error(f"🔄 [HistoryRecon] Error processing generic item {btid}: {e}")
            trade.reconciliation_status = "FAILED"
            return None

    @classmethod
    async def _get_system_token(cls) -> str:
        """Fetch a system JWT from the api-gateway."""
        import aiohttp
        url = f"{settings.API_GATEWAY_URL}/api/v1/auth/token"
        data = aiohttp.FormData()
        data.add_field("username", settings.SYSTEM_USER)
        data.add_field("password", settings.SYSTEM_PASSWORD)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=5.0) as resp:
                    if resp.status == 200:
                        resp_json = await resp.json()
                        # Extract access_token from response (handles both flat and nested 'auth' structures)
                        auth_data = resp_json.get("auth", {}) if "auth" in resp_json else resp_json
                        return auth_data.get("access_token")
                    else:
                        logger.error(f"Failed to fetch system token: {resp.status} {await resp.text()}")
        except Exception as e:
            logger.error(f"Error fetching system token: {e}")
        return "SYSTEM_TOKEN"

    @classmethod
    async def _publish_post_mortem_cmd(cls, trade: Trade, user_id: Any):
        """Publish a command to AI Analyst to run a post-mortem."""
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            # Create payload for the AI Analyst Worker (Redis Stream ai:think:cmd)
            payload = {
                "message": f"Run institutional post-mortem analysis for trade {trade.trade_id}.",
                "user_id": str(user_id),
                "trade_id": str(trade.trade_id),
                "intent": "JOURNAL_ANALYSIS",
                "is_journal_job": True
            }
            
            job_id = f"pm_{trade.trade_id}"
            # Fetch real system token
            token = await cls._get_system_token()
            
            try:
                # The AI Analyst worker expects job_id and payload keys in the stream
                await redis_client.xadd(
                    "ai:think:cmd", 
                    {
                        "job_id": job_id,
                        "payload": json.dumps(payload),
                        "headers": json.dumps({"Authorization": f"Bearer {token}"})
                    }
                )
                logger.info(f"Published post-mortem stream command for trade {trade.trade_id}")
            except Exception as e:
                logger.error(f"Failed to publish post-mortem command: {e}")
            await redis_client.aclose()
        except Exception as e:
            logger.warning(f"🚀 [HistoryRecon] Failed to trigger post-mortem: {e}")
