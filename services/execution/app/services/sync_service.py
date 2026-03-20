import logging
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.future import select
from app.models import BrokerAccount, Trade, TradeStatus, TradeDirection
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.database import AsyncSessionLocal
from app.core.config import settings
from app.core.units import UnitConverter
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class SyncService:
    @classmethod
    async def reconcile_all_funds(cls):
        """
        High-level reconciliation across all funds and their linked brokers.
        Detects Ghost Trades and Broker-to-Broker drifts.
        """
        logger.info("📡 [SyncService] Starting cross-broker synchronization...")
        
        async with AsyncSessionLocal() as db:
            # 1. Fetch all active broker accounts
            stmt = select(BrokerAccount).where(BrokerAccount.is_active)
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            if not accounts:
                logger.info("📡 [SyncService] No active accounts found.")
                return

            # Group accounts by Fund ID for cross-broker comparison
            fund_map: Dict[str, List[BrokerAccount]] = {}
            for acc in accounts:
                fid = str(acc.fund_id)
                if fid not in fund_map:
                    fund_map[fid] = []
                fund_map[fid].append(acc)

            for fund_id, fund_accounts in fund_map.items():
                await cls.reconcile_fund(fund_id, fund_accounts, db)

    @classmethod
    async def reconcile_fund(cls, fund_id: str, accounts: List[BrokerAccount], db):
        """
        Sync all accounts linked to a specific fund.
        """
        logger.info(f"📡 [SyncService] Syncing Fund {fund_id} across {len(accounts)} brokers.")
        
        broker_states: Dict[str, List[Dict[str, Any]]] = {}
        
        # 1. Fetch live states from all brokers in parallel
        async def fetch_state(acc: BrokerAccount):
            try:
                creds = decrypt_data(acc.credentials_encrypted)
                creds["environment"] = acc.environment
                adapter = BrokerFactory.get_adapter(acc.broker_name, creds)
                trades = await adapter.get_open_trades()
                return str(acc.id), trades
            except Exception as e:
                logger.error(f"📡 [SyncService] Failed to fetch state for account {acc.id}: {e}")
                return str(acc.id), None

        tasks = [fetch_state(acc) for acc in accounts]
        results = await asyncio.gather(*tasks)
        
        for acc_id, trades in results:
            if trades is not None:
                broker_states[acc_id] = trades

        # 2. Fetch DB state for this fund
        account_ids = [acc.id for acc in accounts]
        db_stmt = select(Trade).where(
            Trade.broker_account_id.in_(account_ids),
            Trade.status == TradeStatus.OPEN
        )
        db_result = await db.execute(db_stmt)
        db_trades = db_result.scalars().all()
        db_trade_ids = {str(t.broker_trade_id) for t in db_trades if t.broker_trade_id}

        # 3. Drift Detection Logic
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        for acc_id, live_trades in broker_states.items():
            account = next(a for a in accounts if str(a.id) == acc_id)
            
            for lt in live_trades:
                btid = str(lt.get("id"))
                
                # A. Ghost Trade Detection: In Broker but NOT in DB
                if btid not in db_trade_ids:
                    msg = f"‼️ [GHOST TRADE] {account.broker_name} {account.account_name}: Trade {btid} ({lt.get('symbol')}, {lt.get('units')} units) exists in broker but MISSING in DB."
                    logger.warning(msg)
                    
                    # [AUTO-SYNC] Create DB record for ghost trade
                    try:
                        await cls._create_ghost_trade_record(lt, account, db)
                        logger.info(f"✅ [AUTO-SYNC] Created DB record for ghost trade {btid}")
                    except Exception as e:
                        logger.error(f"❌ [AUTO-SYNC] Failed to create ghost trade record: {e}")
                    
                    # Publish Critical Drift to Redis for UI/Alerting
                    alert = {
                        "type": "GHOST_TRADE",
                        "fund_id": fund_id,
                        "account_id": acc_id,
                        "broker": account.broker_name,
                        "symbol": lt.get("symbol"),
                        "broker_trade_id": btid,
                        "units": lt.get("units"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await redis_client.xadd("system.alerts.drift", {"payload": json.dumps(alert)})

                # B. SL/TP Consistency (TODO: Future refinement)

        # 4. Cross-Broker Net Exposure Drift (e.g. OANDA long 1.0, cTrader long 0.5 -> Drift 0.5)
        # This is for funds that are supposed to be mirrors or hedged.
        # For now, we log the net exposure per asset per fund.
        await cls._calculate_net_exposure_drift(fund_id, broker_states, redis_client)
        
        await redis_client.close()

    @classmethod
    async def _calculate_net_exposure_drift(cls, fund_id: str, broker_states: Dict[str, List[Dict[str, Any]]], redis_client):
        net_exposure: Dict[str, Dict[str, float]] = {} # symbol -> {account_id -> units}
        
        for acc_id, trades in broker_states.items():
            for t in trades:
                symbol = t.get("symbol")
                units = float(t.get("units", 0))
                if symbol not in net_exposure:
                    net_exposure[symbol] = {}
                net_exposure[symbol][acc_id] = net_exposure[symbol].get(acc_id, 0.0) + units
        
        for symbol, accounts in net_exposure.items():
            if len(accounts) > 1:
                # Compare exposures
                exposures = list(accounts.values())
                if len(set(exposures)) > 1:
                    max_val = max(exposures)
                    min_val = min(exposures)
                    max_drift = max_val - min_val
                    
                    # Institutional Tolerance: 10% relative drift or $100 equivalent (simplified)
                    relative_drift = (max_drift / abs(max_val)) if max_val != 0 else 0
                    
                    if relative_drift > 0.1: # 10% threshold
                        logger.error(f"🚨 [CRITICAL DRIFT] Fund {fund_id} | {symbol}: Drift {relative_drift:.2%} ({max_drift:.4f} units) across brokers.")
                        
                        drift_alert = {
                            "type": "EXPOSURE_DRIFT",
                            "severity": "CRITICAL",
                            "fund_id": fund_id,
                            "symbol": symbol,
                            "drift_units": max_drift,
                            "relative_drift": relative_drift,
                            "details": accounts,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await redis_client.xadd("system.alerts.drift", {"payload": json.dumps(drift_alert)})
                    elif max_drift > 0.0001:
                        logger.warning(f"⚖️ [EXPOSURE DRIFT] Fund {fund_id} | {symbol}: Minor Drift {max_drift:.4f} units.")

    @classmethod
    async def _create_ghost_trade_record(cls, live_trade: Dict[str, Any], account: BrokerAccount, db):
        """
        Create a DB record for a ghost trade detected from broker but missing in Olympus DB.
        This auto-syncs positions created outside of Olympus.
        """
        import uuid
        
        # Determine direction from broker side
        side = live_trade.get("side", "BUY")
        direction = TradeDirection.LONG if side.upper() == "BUY" else TradeDirection.SHORT
        
        # [VOL-Normalization] Use Centralized Pro UnitConverter
        units = float(live_trade.get("units", 0))
        lot_size = UnitConverter.internal_to_standard_lots(units)
        
        # Get price (entry price from broker)
        entry_price = float(live_trade.get("price", 0))
        
        # Convert sl/tp if present
        sl_price = None
        if live_trade.get("sl"):
            sl_price = float(live_trade.get("sl"))
        
        tp_price = None
        if live_trade.get("tp"):
            tp_price = float(live_trade.get("tp"))
        
        # Deterministic UUID — matches worker.py for cross-service merge
        trade_uuid = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"{str(account.id)}_{str(live_trade.get('id'))}"
        )
        
        # Create the trade record
        trade = Trade(
            trade_id=trade_uuid,
            broker_account_id=account.id,
            broker_trade_id=str(live_trade.get("id")),
            symbol=live_trade.get("symbol", "UNKNOWN"),
            strategy_name="GHOST_SYNC",  # Placeholder for auto-synced trades
            signal_timestamp=datetime.utcnow(),
            is_shadow=True,  # Mark as broker-synced (not created by Olympus)
            status=TradeStatus.OPEN,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            lot_size=lot_size,
            risk_usd=0,  # Unknown risk for ghost trades
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        
        logger.info(f"📝 [AUTO-SYNC] Ghost trade created: {trade.trade_id} | {trade.symbol} {trade.direction} {lot_size} lots @ {entry_price}")
        return trade

sync_service = SyncService()
