import json
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.future import select
from app.models import Trade, TradeStatus, User, UserPreferences
from app.database import AsyncSessionLocal
from app.utils.crypto import decrypt_data
from datetime import datetime

logger = logging.getLogger(__name__)

class OandaStreamer:
    def __init__(self, account_id: str, api_key: str, environment: str = "practice"):
        self.account_id = account_id
        self.api_key = api_key
        self.environment = environment.lower()
        # OANDA v20 streaming URLs: stream-fxpractice for practice, stream-fxtrade for live
        if self.environment in ["live", "production"]:
            self.base_url = "https://stream-fxtrade.oanda.com"
        else:
            self.base_url = "https://stream-fxpractice.oanda.com"
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the streaming listener in a background task."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"📡 [Streamer] Started OANDA stream for account {self.account_id}")

    async def stop(self):
        """Stop the streaming listener."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"📡 [Streamer] Stopped OANDA stream for account {self.account_id}")

    async def _run(self):
        """Main streaming loop."""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/transactions/stream"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        while self.is_running:
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", url, headers=headers) as response:
                        if response.status_code != 200:
                            logger.error(f"📡 [Streamer] OANDA Stream Err: {response.status_code}")
                            await asyncio.sleep(10)
                            continue
                            
                        async for line in response.aiter_lines():
                            if not self.is_running:
                                break
                            if not line:
                                continue
                                
                            try:
                                event = json.loads(line)
                                if event.get("type") == "HEARTBEAT":
                                    continue
                                    
                                await self._handle_event(event)
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                logger.error(f"📡 [Streamer] Event Handle Error: {e}")
                                
            except Exception as e:
                logger.error(f"📡 [Streamer] Connection Error: {e}. Retrying in 10s...")
                await asyncio.sleep(10)

    async def _handle_event(self, event: Dict[str, Any]):
        """Parse OANDA transaction events and update Olympus DB."""
        etype = event.get("type")
        
        # We are interested in events that change trade state
        # See OANDA API Docs: ORDER_FILL, TRADE_CLOSE, etc.
        if etype == "ORDER_FILL":
            trade_opened = event.get("tradeOpened")
            trade_closed = event.get("tradesClosed") # List for partials or full close
            
            if trade_closed:
                for tc in trade_closed:
                    await self._process_trade_close(tc.get("tradeID"), event)
            
            # Note: We don't usually open trades via stream (we open via API), 
            # but if it was a LIMIT order filling, we might want to update its status.
            if trade_opened:
                # Handle limit order fill if needed
                pass

        elif etype == "TRADE_CLOSE":
            await self._process_trade_close(event.get("tradeID"), event)

    async def _process_trade_close(self, broker_trade_id: str, event: Dict[str, Any]):
        """Update DB when a trade is closed on OANDA (SL, TP, or Manual)."""
        if not broker_trade_id:
            return
            
        async with AsyncSessionLocal() as db:
            # Find the trade in Olympus DB by broker_trade_id
            stmt = select(Trade).where(Trade.broker_trade_id == str(broker_trade_id))
            result = await db.execute(stmt)
            trade = result.scalar_one_or_none()
            
            if trade and trade.status == TradeStatus.OPEN:
                logger.info(f"📉 [Streamer] Real-time Sync: Trade {trade.trade_id} (Broker: {broker_trade_id}) closed on OANDA. Updating Olympus.")
                
                trade.status = TradeStatus.CLOSED
                trade.exit_timestamp = datetime.utcnow()
                
                # Try to extract PnL from event
                pnl = event.get("pl") or event.get("rpl") # Realized PL
                if pnl:
                    trade.pnl_usd = float(pnl)
                
                if not trade.metadata_json:
                    trade.metadata_json = {}
                trade.metadata_json['stream_close'] = True
                trade.metadata_json['event_type'] = event.get("type")
                
                await db.commit()

class MultiStreamManager:
    """Manages transaction streams for multiple accounts."""
    _streams: Dict[str, OandaStreamer] = {}

    @classmethod
    async def sync_streams(cls):
        """Enable streams for all eligible accounts."""
        async with AsyncSessionLocal() as db:
            # Eligibility check (same as Janitor)
            from app.models import BrokerAccount, Fund, UserFund
            stmt = (
                select(BrokerAccount)
                .join(Fund, BrokerAccount.fund_id == Fund.id)
                .join(UserFund, Fund.id == UserFund.fund_id)
                .join(User, UserFund.user_id == User.id)
                .join(UserPreferences, User.id == UserPreferences.user_id)
                .where(
                    BrokerAccount.broker_name == "OANDA",
                    BrokerAccount.is_active == True,
                    User.is_active == True,
                    UserPreferences.oanda_janitor_enabled == True
                )
            )
            result = await db.execute(stmt)
            eligible_accounts = result.scalars().all()
            
            eligible_ids = {str(a.id) for a in eligible_accounts}
            current_ids = set(cls._streams.keys())
            
            # Stop streams for no-longer eligible accounts
            for aid in current_ids - eligible_ids:
                await cls._streams[aid].stop()
                del cls._streams[aid]
                
            # Start streams for new eligible accounts
            for account in eligible_accounts:
                aid = str(account.id)
                if aid not in cls._streams:
                    credentials = decrypt_data(account.credentials_encrypted)
                    streamer = OandaStreamer(
                        account_id=account.account_number,
                        api_key=credentials.get("api_key"),
                        environment=account.environment or "practice"
                    )
                    cls._streams[aid] = streamer
                    await streamer.start()
