import sys
import os
import argparse
import logging
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, engine
from app.adapters.oanda import OandaClient
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.models.candle import Candle

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def resolve_market_symbol(session, symbol: str, source_name: str = "OANDA"):
    """
    Resolve MarketSymbol ID for a given symbol and data source.
    """
    stmt = (
        select(MarketSymbol)
        .join(DataSource)
        .where(MarketSymbol.symbol == symbol)
        .where(DataSource.name == source_name)
    )
    result = session.execute(stmt).scalar_one_or_none()
    
    if not result:
        # Try finding by name to handle XAU/USD vs XAU_USD mismatch if strictly needed,
        # but OANDA adapter usually expects normalized names.
        # Check if the symbol exists with different formatting
        alt_stmt = (
            select(MarketSymbol)
            .join(DataSource)
            .where(MarketSymbol.symbol == symbol.replace('/', '_'))
            .where(DataSource.name == source_name)
        )
        result = session.execute(alt_stmt).scalar_one_or_none()

    return result

def parse_oanda_time(time_str: str) -> datetime:
    """Parse OANDA API timestamp string to datetime object."""
    # Example: "2023-10-25T10:00:00.000000000Z"
    return datetime.strptime(time_str[:26] + 'Z', '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

def backfill_candles(symbol: str, timeframe: str, count: int):
    session = SessionLocal()
    client = OandaClient()

    try:
        # 1. Resolve Dependencies
        logger.info(f"Resolving symbol {symbol} for OANDA...")
        market_symbol = resolve_market_symbol(session, symbol)
        
        if not market_symbol:
            logger.error(f"MarketSymbol '{symbol}' not found for OANDA. Please ensure it exists in 'market_symbols' table.")
            # Optional: Auto-create logic could go here, but safer to fail for now.
            return

        ms_id = market_symbol.id
        logger.info(f"Found MarketSymbol ID: {ms_id}")

        # 2. Fetch Data from OANDA
        logger.info(f"Fetching {count} candles for {symbol} ({timeframe})...")
        candles_data = client.fetch_candles(symbol, timeframe, count=count)
        
        if not candles_data:
            logger.warning("No candles returned from OANDA.")
            return

        logger.info(f"Received {len(candles_data)} candles. Preparing upsert...")

        # 3. Transform Data
        upsert_data = []
        for c in candles_data:
            ts = parse_oanda_time(c['time'])
            mid = c['mid']
            
            row = {
                "market_symbol_id": ms_id,
                "timeframe": timeframe,
                "timestamp": ts,
                "open": float(mid['o']),
                "high": float(mid['h']),
                "low": float(mid['l']),
                "close": float(mid['c']),
                "volume": int(c['volume']),
                "is_complete": c['complete']
            }
            upsert_data.append(row)

        # 4. Batch Upsert
        # PostgreSQL ON CONFLICT DO UPDATE
        stmt = insert(Candle).values(upsert_data)
        
        update_dict = {
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "is_complete": stmt.excluded.is_complete,
            "updated_at": datetime.now(timezone.utc)
        }

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
            set_=update_dict
        )

        result = session.execute(upsert_stmt)
        session.commit()
        
        logger.info(f"Successfully upserted {len(upsert_data)} candles.")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill candles from OANDA")
    parser.add_argument("--symbol", type=str, required=True, help="Instrument symbol (e.g. XAU_USD)")
    parser.add_argument("--timeframe", type=str, required=True, help="Timeframe (e.g. H1, M15)")
    parser.add_argument("--count", type=int, default=500, help="Number of candles to fetch")
    
    args = parser.parse_args()
    
    backfill_candles(args.symbol, args.timeframe, args.count)
