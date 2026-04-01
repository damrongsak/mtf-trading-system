from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid
import logging
import traceback

from fastapi import HTTPException

from app.repositories.candle_repository import CandleRepository
from app.repositories.market_repository import MarketRepository
from app.services.loader import load_candles_from_csv, CsvValidationError
from app.services.market_service import MarketService
from app.schemas import PaginationResponse, CandleResponse

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
        except CsvValidationError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Processing error in load_candles_from_csv: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

        # 3. Convert to Dicts & Apply Scaling (Institutional Basis Adjustment)
        is_gold = any(s in symbol.upper() for s in ["XAU", "GOLD", "OG", "GC"])
        
        candle_dicts = []
        now = datetime.utcnow()
        
        for _, row in df.iterrows():
            candle_dicts.append({
                "id": uuid.uuid4(),
                "market_symbol_id": market_symbol.id,
                "symbol": symbol,
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
            broker = MarketService.get_active_broker_name(db)
            if not broker:
                logger.warning("No active data source found when resolving default broker.")
                return PaginationResponse(total=0, page=page, page_size=page_size, data=[])

        # 1. Resolve MarketSymbol
        market_symbol = repo.get_market_symbol(symbol, broker)
        if not market_symbol:
             return PaginationResponse(total=0, page=page, page_size=page_size, data=[])

        # 2. Query
        total = repo.count_candles(market_symbol.id, timeframe)
        candles = repo.get_candles_paginated(market_symbol.id, timeframe, page, page_size)
        
        # 3. Format Response
        data = []
        for c in candles:
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
