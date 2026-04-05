import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.backtest import fetch_data_from_db
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.utils.data_resolver import resolve_source_for_fund

logger = logging.getLogger(__name__)

async def fetch_candles_logic(
    db: Session,
    symbol: str, 
    timeframe: str, 
    user_id: str,
    fund_id: Optional[str] = None,
    limit: int = 200
) -> Tuple[pd.DataFrame, str]:
    """
    Institutional Candle Fetcher.
    Resolves data source based on fund/user context and symbol type (Macro/Forex).

    Returns:
        (df, data_source_name): OHLC DataFrame and the resolved data source label.
    """
    try:
        # 1. Resolve Institutional Data Source
        data_source_name = resolve_source_for_fund(db, user_id, fund_id, symbol)
        
        # 2. Match Symbol and Source in DB
        query = db.query(MarketSymbol).join(DataSource).filter(
            (MarketSymbol.symbol == symbol) | (MarketSymbol.symbol == symbol.replace("/", "_")),
            DataSource.name == data_source_name
        )
        ms = query.first()
        
        if not ms:
            logger.warning(f"Symbol {symbol} not found for source {data_source_name}")
            return pd.DataFrame(), data_source_name
            
        market_symbol_id = ms.id
        
        # 3. Time Range Estimation
        days = 30 
        start_dt = datetime.now(timezone.utc) - pd.Timedelta(days=days)
        end_dt = datetime.now(timezone.utc)
        
        df = fetch_data_from_db(
            market_symbol_id=market_symbol_id, 
            timeframe=timeframe, 
            start_date=start_dt, 
            end_date=end_dt
        )
        
        if df.empty:
            return pd.DataFrame(), data_source_name
            
        # Limit to last N
        df = df.iloc[-limit:] if len(df) > limit else df
        return df, data_source_name
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch candles for {symbol} under fund {fund_id}: {e}")
        return pd.DataFrame(), "UNKNOWN"
