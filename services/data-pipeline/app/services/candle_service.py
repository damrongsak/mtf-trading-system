from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid
from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from app.services.loader import load_candles_from_csv
from app.schemas import PaginationResponse, CandleResponse
from fastapi import HTTPException
import logging
import traceback

logger = logging.getLogger(__name__)

class CandleService:
    @staticmethod
    def process_csv_file(
        file_path: str, 
        symbol: str, 
        timeframe: str, 
        db: Session
    ) -> dict:
        """
        Process a local CSV file: validate, parse, and upsert candles.
        """
        market_repo = MarketRepository(db)
        candle_repo = CandleRepository(db)
        
        # 1. Validate Symbol Exists
        market_symbol = market_repo.get_any_by_symbol(symbol)
        if not market_symbol:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not registered in MarketSymbols.")

        # 2. Parse CSV
        try:
            df = load_candles_from_csv(file_path, symbol, timeframe)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Processing error in load_candles_from_csv: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

        # 3. Convert to Dicts
        candle_dicts = []
        now = datetime.utcnow()
        
        for _, row in df.iterrows():
            candle_dicts.append({
                "id": uuid.uuid4(),
                "market_symbol_id": market_symbol.id,
                "timeframe": row['timeframe'],
                "timestamp": row['timestamp'],
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume'],
                "created_at": now,
                "updated_at": now
            })

        # 4. Bulk Upsert
        try:
            count = candle_repo.bulk_upsert(candle_dicts)
            return {"message": f"Successfully processed {len(df)} rows for {symbol} {timeframe}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database upsert logic failed: {str(e)}")

    @staticmethod
    def get_candles(
        db: Session,
        symbol: str,
        timeframe: str,
        broker: Optional[str],
        page: int,
        page_size: int
    ) -> PaginationResponse:
        repo = CandleRepository(db)
        
        # 0. Resolve Broker if None
        if not broker:
            from app.models.data_source import DataSource
            active_source = db.query(DataSource).filter(DataSource.is_active == True).first()
            if active_source:
                broker = active_source.name
            else:
                # Fallback or error? Let's error clearly.
                # Actually, raising HTTP 404 is cleaner if no source found.
                # But original code returned empty. Let's stick to empty for consistency but log warning.
                logger.warning("No active data source found when resolving default broker.")
                return PaginationResponse(total=0, page=page, page_size=page_size, data=[])

        # 1. Resolve MarketSymbol
        market_symbol = repo.get_market_symbol(symbol, broker)
        if not market_symbol:
             # Basic check if symbol exists at all to give better error (using MarketRepo logic manually or via repo)
             # Let's just return empty as per original logic
             return PaginationResponse(total=0, page=page, page_size=page_size, data=[])

        # 2. Query
        total = repo.count_candles(market_symbol.id, timeframe)
        candles = repo.get_candles_paginated(market_symbol.id, timeframe, page, page_size)
        
        # 3. Format Response
        data = []
        for c in candles:
            # We construct CandleResponse manually or let Pydantic handle it.
            # But the schema expected 'symbol' and 'broker' fields which are not on the Candle model.
            c_dict = {
                "id": c.id,
                "symbol": symbol,
                "broker": broker,
                "timeframe": c.timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "ema_9_4h": c.ema_9_4h,
                "ema_200_4h": c.ema_200_4h,
                "ema_200_d": c.ema_200_d,
                "atr_14_15m": c.atr_14_15m,
                "body_to_wick_ratio": c.body_to_wick_ratio
            }
            data.append(c_dict)

        return PaginationResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=data
        )
