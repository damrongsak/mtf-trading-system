from sqlalchemy.orm import Session
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.models.journal import JournalEntry, GameLevel
from app.models.user import User
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

class TradeService:
    @staticmethod
    def create_trade_from_execution(
        db: Session, 
        user: User, 
        execution_data: Dict[str, Any],
        request_data: Dict[str, Any],
        broker_account_id: Optional[Any] = None
    ) -> Trade:
        """
        Creates a Trade record and a linked JournalEntry stub from an execution result.
        """
        logger.info(f"Creating trade from execution. Request: {request_data}, Execution: {execution_data}")
        
        # Parse direction from units (positive = LONG, negative = SHORT)
        units = float(request_data.get("units", 0))
        direction = TradeDirection.LONG if units > 0 else TradeDirection.SHORT
        logger.debug(f"Determined direction: {direction} from units: {units}")
        
        order_type = request_data.get("order_type", "MARKET")
        status = TradeStatus.OPEN if order_type == "MARKET" else TradeStatus.PENDING
        
        # Deterministic UUID — prevents duplicates across services (Sync/Async paths)
        broker_trade_id = str(execution_data.get("id"))
        
        # Use the passed broker_account_id or fallback to request_data
        acc_id_str = str(broker_account_id) if broker_account_id else str(request_data.get("broker_account_id", "unknown"))
        
        trade_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"{acc_id_str}_{broker_trade_id}"
        )
        
        # Create Trade Record
        trade = Trade(
            trade_id=trade_id,
            symbol=request_data.get("symbol"),
            strategy_name="Manual Execution", # Default for manual trades
            signal_timestamp=datetime.now(timezone.utc),
            status=status,
            direction=direction,
            entry_price=float(execution_data.get("price", 0)), # Actual fill price
            sl_price=request_data.get("sl_price"),
            tp_price=request_data.get("tp_price"),
            lot_size=abs(units) / 100000.0, # Approx lot size (simplified)
            risk_usd=10.0, # Default risk cap from specs
            pnl_usd=None,
            broker_trade_id=str(execution_data.get("id")),
            metadata_json={
                "oanda_id": execution_data.get("id"),
                "execution_time": execution_data.get("time")
            }
        )
        db.add(trade)
        
        # Create Journal Entry Stub
        journal_entry = JournalEntry(
            id=uuid.uuid4(),
            user_id=user.id,
            symbol=trade.symbol,
            direction=trade.direction.value,
            entry_price=trade.entry_price,
            risk_amount=trade.risk_usd,
            stop_loss_price=trade.sl_price,
            take_profit_price=trade.tp_price,
            session="NEW_YORK", # Defaulting/Guessing for now
            game_level=GameLevel.B_GAME, # Default
            created_at=datetime.now(timezone.utc)
            # Note: We should ideally link this to trade_id if schema supported it
            # For now, implicit link via symbol/time/user
        )
        db.add(journal_entry)
        
        db.commit()
        db.refresh(trade)
        logger.info(f"Successfully created trade {trade.trade_id} for symbol {trade.symbol}")
        return trade

    @staticmethod
    def close_trade(db: Session, trade_id: str, exit_price: float) -> Optional[Trade]:
        """
        Manually closes a trade for MVP PnL tracking.
        """
        trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
        if not trade:
            logger.warning(f"Attempted to close non-existent trade: {trade_id}")
            return None
            
        if trade.status == TradeStatus.CLOSED:
            logger.info(f"Trade {trade_id} is already CLOSED.")
            return trade

        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.now(timezone.utc)
        trade.status = TradeStatus.CLOSED
        
        # Calculate PnL (Simplified linear calculation)
        # PnL = (Exit - Entry) * Units * (Conversion if needed)
        # Using simplified lot-based calc: (pips gained) * ($10/pip per lot)
        # This is a Rough Approximation for MVP
        
        multiplier = 1 if trade.direction == TradeDirection.LONG else -1
        diff = (exit_price - float(trade.entry_price)) * multiplier
        
        # Assuming Standard Lot (100k units) -> $10 per pip
        # Pip size depends on symbol (0.01 for XAU, 0.0001 for EURUSD)
        is_gold = "XAU" in trade.symbol
        pip_size = 0.01 if is_gold else 0.0001
        
        pips = diff / pip_size
        # lot_size is stored, e.g., 0.1
        # Value per pip = lot_size * 10
        value_per_pip = float(trade.lot_size) * 10
        
        trade.pnl_usd = pips * value_per_pip
        
        # Update Metadata
        if not trade.metadata_json:
            trade.metadata_json = {}
        trade.metadata_json["manual_close"] = True
        
        db.commit()
        db.refresh(trade)
        logger.info(f"Closed trade {trade.trade_id}. PnL: {trade.pnl_usd}")
        return trade

    @staticmethod
    def sync_open_trades(db: Session, broker_trades: list, user: User, broker_account_id: uuid.UUID = None) -> list[Trade]:
        """
        Syncs open trades from execution service to local database.
        Uses upsert logic based on 'broker_trade_id'.
        """
        logger.info(f"Syncing {len(broker_trades)} open trades for account {broker_account_id}")
        synced_trades = []
        
        for bt in broker_trades:
            broker_id = str(bt.get("id"))
            if not broker_id:
                continue
                
            # Check if trade exists by broker_trade_id
            existing_trade = db.query(Trade).filter(
                Trade.status == TradeStatus.OPEN,
                Trade.broker_trade_id == broker_id
            ).first()
            
            # Fallback for old Oanda trades stored only in metadata (Migration support)
            if not existing_trade:
                existing_trade = db.query(Trade).filter(
                    Trade.status == TradeStatus.OPEN,
                    Trade.metadata_json['oanda_id'].astext == broker_id
                ).first()
            
            if existing_trade:
                # Update SL/TP if they exist in the incoming data
                if "sl" in bt and bt["sl"] is not None:
                    existing_trade.sl_price = float(bt["sl"])
                if "tp" in bt and bt["tp"] is not None:
                    existing_trade.tp_price = float(bt["tp"])
                
                if broker_account_id and not existing_trade.broker_account_id:
                    existing_trade.broker_account_id = broker_account_id
                
                if not existing_trade.broker_trade_id:
                    existing_trade.broker_trade_id = broker_id
                    
                synced_trades.append(existing_trade)
                continue
            
            # Create NEW Trade if we missed it (e.g. opened externally)
            try:
                units = float(bt.get("units") or bt.get("currentUnits") or 0)
                direction = bt.get("direction")
                if not direction:
                    direction = TradeDirection.LONG if units > 0 else TradeDirection.SHORT
                elif isinstance(direction, str):
                    direction = TradeDirection.LONG if direction.upper() in ["LONG", "BUY"] else TradeDirection.SHORT
                
                entry_price = float(bt.get("entry_price") or bt.get("price") or 0)
                
                new_trade = Trade(
                    trade_id=uuid.uuid4(),
                    broker_account_id=broker_account_id,
                    broker_trade_id=broker_id,
                    symbol=bt.get("symbol") or bt.get("instrument", "UNKNOWN"),
                    strategy_name="External Sync",
                    signal_timestamp=datetime.now(timezone.utc),
                    status=TradeStatus.OPEN,
                    direction=direction,
                    entry_price=entry_price,
                    sl_price=float(bt.get("sl") or 0),
                    tp_price=float(bt.get("tp") or 0),
                    lot_size=abs(units) / 100000.0,
                    risk_usd=0.0,
                    metadata_json={
                        "broker_id": broker_id,
                        "sync_source": "API_SYNC",
                        "open_time": bt.get("time") or bt.get("openTime")
                    }
                )
                db.add(new_trade)
                synced_trades.append(new_trade)
                logger.info(f"Imported external trade {broker_id} for {new_trade.symbol}")
                
            except Exception as e:
                logger.error(f"Failed to import external trade {broker_id}: {e}")
                
        db.commit()
        return synced_trades

