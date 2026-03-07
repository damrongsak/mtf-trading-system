from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.candle import Candle
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
import logging

logger = logging.getLogger(__name__)

class CandleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_market_symbol(self, symbol: str, broker: str) -> Optional[MarketSymbol]:
        """
        Resolve MarketSymbol by symbol name and broker.
        Handles OANDA v20 format (underscore) vs Standard (slash).
        """
        # 1. Direct match
        ms = self.db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol == symbol,
            DataSource.name == broker
        ).first()

        if ms:
            return ms

        # 2. Try normalized (slash -> underscore)
        if "/" in symbol:
            normalized_symbol = symbol.replace("/", "_")
            ms = self.db.query(MarketSymbol).join(DataSource).filter(
                MarketSymbol.symbol == normalized_symbol,
                DataSource.name == broker
            ).first()
            if ms:
                return ms
        
        return None

    def count_candles(self, market_symbol_id: Any, timeframe: str) -> int:
        return self.db.query(Candle).filter(
            Candle.market_symbol_id == market_symbol_id,
            Candle.timeframe == timeframe
        ).count()

    def get_candles_paginated(
        self, 
        market_symbol_id: Any, 
        timeframe: str, 
        page: int, 
        page_size: int
    ) -> List[Candle]:
        return self.db.query(Candle).filter(
            Candle.market_symbol_id == market_symbol_id,
            Candle.timeframe == timeframe
        ).order_by(Candle.timestamp.desc())\
         .offset((page - 1) * page_size)\
         .limit(page_size)\
         .all()

    def get_latest_candle(self, market_symbol_id: Any, timeframe: str) -> Optional[Candle]:
        """Get the most recent candle for a symbol and timeframe."""
        return self.db.query(Candle).filter(
            Candle.market_symbol_id == market_symbol_id,
            Candle.timeframe == timeframe
        ).order_by(Candle.timestamp.desc()).first()

    def bulk_upsert(self, candles_data: List[Dict[str, Any]]) -> int:
        """
        Bulk insert/upsert candles.
        Returns number of records processed.
        """
        if not candles_data:
            return 0

        stmt = insert(Candle).values(candles_data)
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
            set_={
                'symbol': stmt.excluded.symbol,
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'is_complete': stmt.excluded.is_complete,
                'updated_at': datetime.utcnow()
            }
        )
        
        try:
            self.db.execute(do_update_stmt)
            self.db.commit()
            return len(candles_data)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Bulk upsert failed: {e}")
            raise e
