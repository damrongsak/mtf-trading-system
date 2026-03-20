import logging
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.future import select
from app.models import BrokerAccount, Trade, TradeStatus, TradeDirection, Fund
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

        # 2. Fetch DB state for this fund (Fetch all to avoid ghost duplicates for closed trades)
        account_ids = [acc.id for acc in accounts]
        db_stmt = select(Trade.broker_trade_id).where(
            Trade.broker_account_id.in_(account_ids)
        )
        db_result = await db.execute(db_stmt)
        db_trade_ids = {str(row[0]) for row in db_result.all() if row[0]}

        # 3. Fetch Fund for settings
        fund = await db.get(Fund, fund_id)
        auto_protect = getattr(fund, "auto_protect_enabled", False)
        emergency_pips = float(getattr(fund, "emergency_sl_pips", 500.0))

        # 4. Drift Detection & Auto-Protect Logic
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        for acc_id, live_trades in broker_states.items():
            account = next(a for a in accounts if str(a.id) == acc_id)
            creds = decrypt_data(account.credentials_encrypted)
            creds["environment"] = account.environment
            adapter = BrokerFactory.get_adapter(account.broker_name, creds)
            
            for lt in live_trades:
                btid = str(lt.get("id") or lt.get("broker_trade_id"))
                
                # [AUTO-PROTECT] Check if trade needs emergency SL
                if auto_protect and not lt.get("sl"):
                    try:
                        # Fetch current price or entry to calculate SL
                        entry_p = float(lt.get("price", 0))
                        symbol = lt.get("symbol")
                        side = lt.get("side", "BUY")
                        
                        if entry_p > 0:
                            # Resolution: Need pip value for this symbol
                            # cTrader adapter knows this via its internal cache
                            _, _, _, digits = await adapter._resolve_symbol_id_and_lot_size(symbol)
                            # Simple pip calc: 10^-digits * 10 (pip is usually 10 points)
                            # For Gold (2 digits), point is 0.01. 500 pips = 50.0 points.
                            # For FX (5 digits), point is 0.00001. 500 pips = 0.00500.
                            # Standard MTF rule: 1.0 point = 10 pips.
                            point_value = 10 ** -digits
                            sl_dist = emergency_pips * point_value * 10
                            
                            new_sl = entry_p - sl_dist if side.upper() == "BUY" else entry_p + sl_dist
                            new_sl = round(new_sl, digits)
                            
                            logger.info(f"🛡️ [Auto-Protect] Applying emergency SL {new_sl} to {symbol} trade {btid}")
                            await adapter.amend_position(btid, sl_price=new_sl)
                            # Update lt so consistency check below sees it
                            lt["sl"] = new_sl
                    except Exception as protect_err:
                        logger.error(f"🛡️ [Auto-Protect] Failed to protect trade {btid}: {protect_err}")

                # A. Ghost Trade Detection: In Broker but NOT in DB
                if btid not in db_trade_ids:
                    msg = f"‼️ [GHOST TRADE] {account.broker_name} {account.account_name}: Trade {btid} ({lt.get('symbol')}, {lt.get('units')} units) exists in broker but MISSING in DB."
                    logger.warning(msg)
                    
                    # [AUTO-SYNC] Create DB record for ghost trade
                    try:
                        async with db.begin_nested():
                            await cls._create_ghost_trade_record(lt, account, db)
                        logger.info(f"✅ [AUTO-SYNC] Created DB record for ghost trade {btid}")
                        db_trade_ids.add(btid) # Prevent multiple attempts in same loop
                    except Exception as e:
                        logger.error(f"❌ [AUTO-SYNC] Failed to create ghost trade record {btid}: {e}")
                    
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

                # B. SL/TP Consistency
                else:
                    # Trade exists in DB, check for missing or different SL/TP
                    # Only check OPEN trades in DB for SL/TP consistency
                    db_open_stmt = select(Trade).where(
                        Trade.broker_account_id == account.id,
                        Trade.broker_trade_id == btid,
                        Trade.status == TradeStatus.OPEN
                    )
                    db_open_res = await db.execute(db_open_stmt)
                    db_trade = db_open_res.scalars().first()
                    
                    if db_trade:
                        needs_update = False
                        
                        # Sync SL
                        live_sl = float(lt.get("sl")) if lt.get("sl") else None
                        if live_sl and (not db_trade.sl_price or abs(float(db_trade.sl_price) - live_sl) > 0.00001):
                            db_trade.sl_price = live_sl
                            needs_update = True
                            
                        # Sync TP
                        live_tp = float(lt.get("tp")) if lt.get("tp") else None
                        if live_tp and (not db_trade.tp_price or abs(float(db_trade.tp_price) - live_tp) > 0.00001):
                            db_trade.tp_price = live_tp
                            needs_update = True
                            
                        # If SL/TP updated, recalculate risk
                        if needs_update:
                            if db_trade.sl_price and db_trade.entry_price:
                                price_diff = abs(float(db_trade.entry_price) - float(db_trade.sl_price))
                                # In cTrader logic used by UnitConverter.calculate_risk_usd:
                                # risk = price_diff * (volume_cents / 100.0)
                                # since 1.0 lot = 100,000 cents, volume_cents = lot_size * 100,000
                                volume_cents = float(db_trade.lot_size) * 100000.0
                                db_trade.risk_usd = UnitConverter.calculate_risk_usd(price_diff, volume_cents)
                                
                                if db_trade.tp_price and price_diff > 0:
                                    tp_distance = abs(float(db_trade.tp_price) - float(db_trade.entry_price))
                                    db_trade.rr_ratio = round(tp_distance / price_diff, 2)
                            
                            db_trade.updated_at = datetime.utcnow()
                            # db.commit() removed - committed once at the end
                            logger.info(f"🔄 [AUTO-SYNC] Updated SL/TP/Risk for trade {btid} in DB.")
        
        # 4. Final Commit for all changes in this fund
        try:
            await db.commit()
            logger.info(f"✅ [SyncService] Fund {fund_id} reconciliation changes committed.")
        except Exception as commit_err:
            logger.error(f"❌ [SyncService] Failed to commit changes for Fund {fund_id}: {commit_err}")
            await db.rollback()

        # 5. Cross-Broker Net Exposure Drift (e.g. OANDA long 1.0, cTrader long 0.5 -> Drift 0.5)
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
                # Use lot_size (standardized) for exposure comparison across brokers
                units = float(t.get("lot_size", 0))
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

        # [RISK-Calculation] Calculate risk for ghost trades if SL is present
        risk_usd = 0.0
        rr_ratio = None
        if sl_price and entry_price:
            price_diff = abs(entry_price - sl_price)
            risk_usd = UnitConverter.calculate_risk_usd(price_diff, units)
            
            if tp_price and price_diff > 0:
                tp_distance = abs(tp_price - entry_price)
                rr_ratio = round(tp_distance / price_diff, 2)
        
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
            risk_usd=risk_usd,
            rr_ratio=rr_ratio,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(trade)
        # db.commit() and refresh() removed - managed by caller's transaction
        
        logger.info(f"📝 [AUTO-SYNC] Ghost trade created: {trade.trade_id} | {trade.symbol} {trade.direction} {lot_size} lots @ {entry_price}")
        return trade

sync_service = SyncService()
