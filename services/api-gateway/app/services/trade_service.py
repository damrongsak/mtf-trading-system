from sqlalchemy.orm import Session
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.models.journal import JournalEntry, GameLevel
from app.models.user_fund import User
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

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
        # Parse direction from units (positive = LONG, negative = SHORT)
        units = float(request_data.get("units", 0))
        direction = TradeDirection.LONG if units > 0 else TradeDirection.SHORT
        
        # Create Trade Record
        trade = Trade(
            trade_id=uuid.uuid4(),
            symbol=request_data.get("symbol"),
            strategy_name="Manual Execution", # Default for manual trades
            signal_timestamp=datetime.utcnow(),
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
            created_at=datetime.utcnow()
            # Note: We should ideally link this to trade_id if schema supported it
            # For now, implicit link via symbol/time/user
        )
        db.add(journal_entry)
        
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def close_trade(db: Session, trade_id: str, exit_price: float) -> Optional[Trade]:
        """
        Manually closes a trade for MVP PnL tracking.
        """
        trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
        if not trade:
            return None
            
        if trade.status == TradeStatus.CLOSED:
            return trade

        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.utcnow()
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
        return trade
