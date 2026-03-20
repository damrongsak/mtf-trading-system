
import logging
import json
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from redis.asyncio import Redis
import aiohttp
from scipy import stats
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models import Fund, BrokerAccount, Trade, TradeStatus, DataSource
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class EquityCurveProjections:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.curve_key_prefix = "equity_guardian:curve:"
        self.metrics_key_prefix = "equity_guardian:metrics:"

    async def get_curve(self, account_id: str) -> pd.DataFrame:
        """Fetch equity curve from Redis."""
        key = f"{self.curve_key_prefix}{account_id}"
        # LRANGE 0 -1 to get all
        raw_data = await self.redis.lrange(key, 0, -1)
        if not raw_data:
            return pd.DataFrame()
        
        # Parse JSON
        records = [json.loads(d) for d in raw_data]
        df = pd.DataFrame(records)
        if not df.empty:
             df['timestamp'] = pd.to_datetime(df['timestamp'])
             df.sort_values('timestamp', inplace=True)
        return df

    async def update_curve(self, trade: dict):
        """Append a new trade to the equity curve."""
        account_id = trade.get("account_id") or trade.get("broker_account_id")
        if not account_id:
            # logger.error(f"Cannot update curve: trade missing account_id: {trade}")
            # Silently ignore if not relevant context
            return
            
        key = f"{self.curve_key_prefix}{account_id}"
        
        entry = {
            "timestamp": trade.get("close_time", datetime.utcnow().isoformat()),
            "pnl": float(trade.get("pnl") or trade.get("pnl_usd", 0.0)),
            "id": trade.get("id") or trade.get("trade_id")
        }
        
        await self.redis.rpush(key, json.dumps(entry))
        # Trim to keep last 5000 trades
        await self.redis.ltrim(key, -5000, -1)

    async def hydrate(self, account_id: str, token: str):
        """Fetch full history from API Gateway."""
        logger.info(f"Hydrating Equity Curve for {account_id}...")
        # Correct path for trade history in Execution router is /execution/trades
        url = f"{settings.API_GATEWAY_URL}/execution/trades"
        params = {
            "broker_account_id": account_id,
            "per_page": 5000,
            "status": "CLOSED" 
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # TradeService returns data in 'data' field
                        trades = data.get("data", [])
                        
                        # Clear existing
                        key = f"{self.curve_key_prefix}{account_id}"
                        await self.redis.delete(key)
                        
                        # Sort by time asc
                        # trades is a list of dicts from TradeResponse
                        trades.sort(key=lambda x: x.get('exit_timestamp') or x.get('signal_timestamp') or '')
                        
                        pipeline = self.redis.pipeline()
                        for t in trades:
                            entry = {
                                "timestamp": t.get('exit_timestamp') or t.get('signal_timestamp'),
                                "pnl": float(t.get('pnl_usd') or 0.0),
                                "id": str(t.get('trade_id') or t.get('id'))
                            }
                            if entry["timestamp"]:
                                pipeline.rpush(key, json.dumps(entry))
                        
                        await pipeline.execute()
                        logger.info(f"Hydration complete. Loaded {len(trades)} trades.")
                    else:
                        logger.error(f"Failed to hydrate: {resp.status} - {await resp.text()}")
        except Exception as e:
            logger.error(f"Hydration error: {e}")

class EquityGuardian:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.projections = EquityCurveProjections(redis_client)
        self._threshold_cache = {} # fund_id -> float

    async def _listen_for_rebalance(self):
        """[Phase 57] Listen for manual or AI risk rebalancing events."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("system:events")
        logger.info("Equity Guardian: Listening for RISK_REBALANCE_APPLIED...")
        
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = json.loads(message['data'])
                    if data.get('event') == 'RISK_REBALANCE_APPLIED':
                        fund_id = data.get('fund_id')
                        logger.info(f"Equity Guardian: Refreshing thresholds for fund {fund_id}")
                        # Next analyze() will fetch fresh from DB
                        if fund_id in self._threshold_cache:
                            del self._threshold_cache[fund_id]
            except Exception as e:
                logger.error(f"Equity Guardian Listener Error: {e}")
            await asyncio.sleep(0.5)

    async def _get_token(self) -> str:
        """Fetch JWT token from API Gateway."""
        if hasattr(self, '_token') and self._token:
             return self._token
             
        logger.info("Fetching system auth token...")
        url = f"{settings.API_GATEWAY_URL}/auth/token"
        # OAuth2PasswordRequestForm expects username and password
        data = {
            "username": settings.SYSTEM_USER,
            "password": settings.SYSTEM_PASSWORD
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        # The auth response has { "auth": { "access_token": "..." } }
                        self._token = res.get("auth", {}).get("access_token")
                        return self._token
                    else:
                        logger.error(f"Failed to get token: {resp.status} - {await resp.text()}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching token: {e}")
            return None

    async def check_health(self):
        """Standard entry point for Scheduler."""
        logger.info("Equity Guardian: Health Check Started...")
        
        token = await self._get_token()
        if not token:
            logger.error("Skipping health check: Could not authenticate.")
            return

        headers = {"Authorization": f"Bearer {token}"}
        
        # Fetch active accounts
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                 # Listing accounts endpoint is /accounts/ (trailing slash ensures no 307)
                 url = f"{settings.API_GATEWAY_URL}/accounts/"
                 async with session.get(url) as resp:
                     if resp.status == 200:
                         res = await resp.json()
                         accounts = res.get("data", [])
                         
                         for acc in accounts:
                             await self.analyze(acc['id'], token)
                     else:
                         logger.error(f"Failed to fetch accounts: {resp.status} - {await resp.text()}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    async def start_listener(self):
        """Starts the background event listener."""
        asyncio.create_task(self._listen_for_rebalance())

    def _calculate_metrics(self, df: pd.DataFrame) -> dict:
        """
        Synchronous, CPU-bound calculation of equity metrics.
        Executed in a thread pool to avoid blocking the event loop.
        """
        if df.empty or len(df) < 5:
            return None

        # Equity Curve
        df['equity'] = df['pnl'].cumsum()
        
        # K-Ratio
        y = df['equity'].values
        x = np.arange(len(y))
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        if std_err == 0:
            k_ratio = 0
        else:
            k_ratio = slope / std_err
            
        # Drawdown (Relative to start of window)
        rolling_max = df['equity'].cummax()
        drawdown = df['equity'] - rolling_max
        max_drawdown = drawdown.min() # Largest negative dip
        
        # Capture the relative peak where the max drawdown occurred (for % calculation later)
        # We find the index of the min drawdown
        min_dd_idx = drawdown.idxmin()
        peak_at_dd = rolling_max.loc[min_dd_idx]
        
        # Current Drawdown (Relative to current HWM)
        current_equity = df['equity'].iloc[-1]
        current_hwm = rolling_max.iloc[-1]
        current_drawdown_usd = float(current_equity - current_hwm) # Negative or zero
        
        return {
            "updated_at": datetime.utcnow().isoformat(),
            "k_ratio": k_ratio,
            "r_squared": r_squared,
            "max_drawdown_usd": float(max_drawdown),
            "current_drawdown_usd": current_drawdown_usd,
            "peak_relative_usd": float(peak_at_dd),
            "current_hwm_usd": float(current_hwm),
            "total_pnl": float(current_equity),
            "trade_count": len(df)
        }

    async def analyze(self, account_id: str, token: str):
        """Analyze equity curve stability and store metrics."""
        
        # 1. Hydrate if empty
        df = await self.projections.get_curve(account_id)
        if df.empty:
            await self.projections.hydrate(account_id, token)
            df = await self.projections.get_curve(account_id)
            
        if df.empty or len(df) < 5:
            return

        # 2. Fetch Real-time Floating PnL from Broker
        floating_pnl = 0.0
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(BrokerAccount).where(BrokerAccount.id == account_id)
                res = await db.execute(stmt)
                acc = res.scalar_one_or_none()
                if acc:
                    # [HFT-lite] Get credentials and fetch summary
                    credentials = decrypt_data(acc.credentials_encrypted)
                    credentials["environment"] = acc.environment
                    adapter = BrokerFactory.get_adapter(acc.broker_name, credentials)
                    
                    summary = await adapter.get_account_summary()
                    floating_pnl = float(summary.get("unrealized_net", 0.0))
                    
                    # Update balance_snapshot in DB for reconstruction accuracy
                    acc.balance_snapshot = float(summary.get("balance", acc.balance_snapshot))
                    await db.commit()
                    logger.info(f"EquityGuardian: {account_id} Floating PnL=${floating_pnl:.2f}")
        except Exception as e:
            logger.error(f"EquityGuardian: Failed to fetch floating PnL for {account_id}: {e}")

        # 3. Integrate Floating PnL into Curve
        if floating_pnl != 0:
            last_pnl = df['pnl'].iloc[-1]
            # Create a synthetic "floating" record at the end
            floating_row = pd.DataFrame([{
                "timestamp": datetime.utcnow(),
                "pnl": last_pnl + floating_pnl, # Total relative PnL if closed now
                "id": "FLOATING"
            }])
            df = pd.concat([df, floating_row], ignore_index=True)

        # 4. Offload heavy calculations to thread pool
        metrics = await asyncio.to_thread(self._calculate_metrics, df)
        
        if metrics:
            key = f"{self.projections.metrics_key_prefix}{account_id}"
            await self.redis.set(key, json.dumps(metrics))
            logger.info(f"Analyzed {account_id}: K-Ratio={metrics['k_ratio']:.2f}, R2={metrics['r_squared']:.2f}, Current DD={metrics['current_drawdown_usd']:.2f}")

            # 5. Automated Drawdown Enforcement (Institutional Phase 56)
            await self._check_risk_breach(account_id, metrics)

    async def _check_risk_breach(self, account_id: str, metrics: dict):
        """Check if drawdown exceeds institutional limits (Phase 3/Phase 56)."""
        async with AsyncSessionLocal() as db:
            # Fetch fund threshold AND current account snapshot
            stmt = select(Fund, BrokerAccount).join(
                BrokerAccount, Fund.id == BrokerAccount.fund_id
            ).where(BrokerAccount.id == account_id)
            result = await db.execute(stmt)
            res = result.first()
            
            if not res:
                return
            
            fund, account = res
            
            if not fund or not fund.max_drawdown_threshold:
                return

            # Institutional Logic: Threshold is a percentage (e.g. 3.0 means 3%)
            threshold_pct = float(fund.max_drawdown_threshold)
            
            # Use current balance and unrealized PnL to reconstruct the absolute HWM
            current_balance = float(account.balance_snapshot or 0.0)
            total_pnl = float(metrics.get("total_pnl", 0.0))
            current_hwm_rel = float(metrics.get("current_hwm_usd", 0.0))
            current_drawdown_usd = abs(float(metrics.get("current_drawdown_usd", 0.0)))
            
            # Reconstruction:
            # start_balance = current_balance - total_pnl (closed)
            # current_hwm_abs = start_balance + current_hwm_rel
            
            start_balance = current_balance - total_pnl
            current_hwm_abs = start_balance + current_hwm_rel
            
            if current_hwm_abs <= 0:
                logger.warning(f"EquityGuardian: Cannot calculate drawdown for {account_id} (HWM Absolute <= 0)")
                return
                
            current_drawdown_pct = (current_drawdown_usd / current_hwm_abs) * 100
            
            logger.info(f"Risk Check {account_id}: Current DD={current_drawdown_pct:.2f}%, HWM=${current_hwm_abs:.2f}, Threshold={threshold_pct:.2f}%")
            
            if current_drawdown_pct >= threshold_pct:
                logger.critical(f"🚨 [RISK BREACH] Account {account_id} current drawdown ({current_drawdown_pct:.2f}%) exceeded threshold ({threshold_pct:.2f}%)!")
                await self._trigger_hard_stop(fund.id, account_id, f"Current Drawdown % breach: {current_drawdown_pct:.2f}% >= {threshold_pct:.2f}%")

    async def _trigger_hard_stop(self, fund_id: str, account_id: str, reason: str):
        """Halt all trading for the fund and close all positions."""
        logger.warning(f"🛑 [HARD STOP] Triggering emergency halt for Fund {fund_id} due to Account {account_id} breach.")
        
        # 1. Activate Kill Switch in Redis
        halt_key = f"fund:{fund_id}:halted"
        await self.redis.set(halt_key, "1")
        await self.redis.publish("system:events", json.dumps({
            "event": "FUND_HALTED",
            "fund_id": str(fund_id),
            "reason": f"AUTOMATED_HARD_STOP: {reason}"
        }))

        # 2. Urgent: Close all trades for this fund across ALL accounts
        async with AsyncSessionLocal() as db:
            # We need to find all accounts in this fund and close their trades
            acc_stmt = select(BrokerAccount).where(BrokerAccount.fund_id == fund_id)
            acc_result = await db.execute(acc_stmt)
            accounts = acc_result.scalars().all()
            
            from app.adapters.factory import BrokerFactory
            from app.utils.crypto import decrypt_data
            
            for acc in accounts:
                try:
                    credentials = decrypt_data(acc.credentials_encrypted)
                    credentials["environment"] = acc.environment
                    adapter = BrokerFactory.get_adapter(acc.broker_name, credentials)
                    
                    open_trades = await adapter.get_open_trades()
                    for t in open_trades:
                        btid = t.get('id')
                        if btid:
                            logger.info(f"Closing trade {btid} on {acc.broker_name} due to hard stop.")
                            await adapter.close_trade(btid)
                            
                    # Update Olympus DB for closed trades (or let Janitor reconcile later, but better to be proactive)
                    db_stmt = select(Trade).where(Trade.broker_account_id == acc.id, Trade.status == TradeStatus.OPEN)
                    db_result = await db.execute(db_stmt)
                    olympus_trades = db_result.scalars().all()
                    for o_trade in olympus_trades:
                        o_trade.status = TradeStatus.CLOSED
                        o_trade.exit_timestamp = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Failed to close trades for account {acc.id} during hard stop: {e}")
            
            await db.commit()
