from sqlalchemy.orm import Session
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.models.journal import JournalEntry, GameLevel
from app.models.user_fund import User
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
        request_data: Dict[str, Any]
    ) -> Trade:
        """
        Creates a Trade record and a linked JournalEntry stub from an execution result.
        """
        logger.info(f"Creating trade from execution. Request: {request_data}, Execution: {execution_data}")
        
        # Parse direction from units (positive = LONG, negative = SHORT)
        units = float(request_data.get("units", 0))
        direction = TradeDirection.LONG if units > 0 else TradeDirection.SHORT
        logger.debug(f"Determined direction: {direction} from units: {units}")
        
        # Create Trade Record
        trade = Trade(
            trade_id=uuid.uuid4(),
            symbol=request_data.get("symbol"),
            strategy_name="Manual Execution", # Default for manual trades
            signal_timestamp=datetime.now(timezone.utc),
            status=TradeStatus.OPEN,
            direction=direction,
            entry_price=float(execution_data.get("price", 0)), # Actual fill price
            sl_price=request_data.get("sl_price"),
            tp_price=request_data.get("tp_price"),
            lot_size=abs(units) / 100000.0, # Approx lot size (simplified)
            risk_usd=10.0, # Default risk cap from specs
            pnl_usd=None,
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
    def sync_open_trades(db: Session, oanda_trades: list, user: User, broker_account_id: uuid.UUID = None) -> list[Trade]:
        """
        Syncs open trades from Oanda execution service to local database.
        Uses upsert logic based on 'oanda_id'.
        """
        logger.info(f"Syncing {len(oanda_trades)} open trades from Oanda")
        synced_trades = []
        
        for ot in oanda_trades:
            oanda_id = ot.get("id")
            if not oanda_id:
                continue
                
            # Check if trade exists by oanda_id in metadata
            # Ideally we should store oanda_id in a indexed column but for now we search metadata
            # Or assume we rely on trade creation flow first.
            
            # Since JSONB filtering can be slow without index, and we likely don't have many open trades:
            # We can try to match by exact ID if we stored it, or iterate.
            # OPTIMIZATION: Filter by status OPEN first.
            
            # Using JSON path operator ->> to extract field as text
            existing_trade = db.query(Trade).filter(
                Trade.status == TradeStatus.OPEN,
                Trade.metadata_json['oanda_id'].astext == str(oanda_id)
            ).first()
            
            if existing_trade:
                # Update existing (if needed, e.g. current price/pnl if we tracked that live)
                # Ensure broker link if missing
                if broker_account_id and not existing_trade.broker_account_id:
                    existing_trade.broker_account_id = broker_account_id
                
                synced_trades.append(existing_trade)
                continue
            
            # Create NEW Trade if we missed it (e.g. opened externally)
            try:
                units = float(ot.get("currentUnits", 0))
                direction = TradeDirection.LONG if units > 0 else TradeDirection.SHORT
                entry_price = float(ot.get("price", 0))
                
                new_trade = Trade(
                    trade_id=uuid.uuid4(),
                    broker_account_id=broker_account_id,
                    symbol=ot.get("instrument").replace("_", "/"), # Normalize Oanda format
                    strategy_name="Oanda Sync",
                    signal_timestamp=datetime.now(timezone.utc), # Approximate
                    status=TradeStatus.OPEN,
                    direction=direction,
                    entry_price=entry_price,
                    sl_price=0.0, # Not provided in basic list, would need details
                    tp_price=0.0,
                    lot_size=abs(units) / 100000.0,
                    risk_usd=0.0, # Unknown risk
                    metadata_json={
                        "oanda_id": oanda_id,
                        "sync_source": "OANDA_API",
                        "open_time": ot.get("openTime")
                    }
                )
                db.add(new_trade)
                synced_trades.append(new_trade)
                logger.info(f"Imported external Oanda trade {oanda_id} for {new_trade.symbol}")
                
            except Exception as e:
                logger.error(f"Failed to import Oanda trade {oanda_id}: {e}")
                
        db.commit()
        return synced_trades

