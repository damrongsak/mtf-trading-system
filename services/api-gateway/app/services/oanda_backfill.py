import logging
from datetime import datetime
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import pandas as pd
from typing import List, Optional
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models.candle import Candle
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

logger = logging.getLogger(__name__)

class OandaBackfillService:
    def __init__(self, db: Session, data_source: DataSource):
        self.db = db
        self.data_source = data_source
        self.config = data_source.config_json
        
        # Initialize Oanda Client
        hostname = self.config.get("hostname", "api-fxtrade.oanda.com")
        token = self.config.get("token")
        
        if not token:
             raise ValueError("OANDA Token not found in data source config")

        # Determine environment
        env = "practice" if "practice" in hostname else "live"

        self.client = API(access_token=token, environment=env)
        self.account_id = self.config.get("account_id")

    def resolve_market_symbol(self, symbol: str) -> Optional[MarketSymbol]:
        """Find or return None for market symbol."""
        # Check by exact match
        ms = self.db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol == symbol,
            DataSource.id == self.data_source.id
        ).first()
        
        if ms:
            return ms
            
        # Try normalized (XAU/USD vs XAU_USD)
        alt_symbol = symbol.replace('/', '_')
        ms = self.db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol == alt_symbol,
            DataSource.id == self.data_source.id
        ).first()

        return ms

    def fetch_candles(self, symbol: str, timeframe: str, count: int) -> List[dict]:
        """Fetch raw candles from Oanda."""
        logger.info(f"Fetching {count} {timeframe} candles for {symbol}")
        
        # Oanda uses different timeframe notation? e.g. M15, H1. Assuming input matches.
        
        try:
            params = {
                "count": count,
                "granularity": timeframe,
                "price": "M"
            }
            r = instruments.InstrumentsCandles(instrument=symbol, params=params)
            self.client.request(r)
            
            return r.response.get("candles", [])
            
        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}")
            raise e

    def run(self, symbol: str, timeframe: str, count: int):
        """Execute the backfill process."""
        
        # 1. Resolve Symbol
        market_symbol = self.resolve_market_symbol(symbol)
        if not market_symbol:
            logger.warning(f"MarketSymbol {symbol} not found for this source. Auto-creating...")
            # Auto-create logic could go here, or just fail.
            # For backfill convenience, let's create it if missing?
            # Better to fail and ask user to add it, or create it if we are sure?
            # Let's create it to be user friendly.
            market_symbol = MarketSymbol(
                data_source_id=self.data_source.id,
                symbol=symbol,
                name=symbol,
                details={"created_by": "backfill_auto"}
            )
            self.db.add(market_symbol)
            self.db.commit()
            self.db.refresh(market_symbol)
            
        # 2. Fetch Data
        candles = self.fetch_candles(symbol, timeframe, count)
        if not candles:
            logger.warning("No candles received.")
            return

        # 3. Transform & Store
        upsert_data = []
        for c in candles:
            if not c.get('complete', False):
                continue

            ts_str = c['time']
            # Oanda returns nanoseconds (e.g. ...000000000Z), python only supports microseconds (6 digits)
            # Remove Z, truncate to 26 chars (YYYY-MM-DDTHH:MM:SS.mmmmmm), ensure valid ISO
            clean_ts = ts_str.replace('Z', '')
            if '.' in clean_ts and len(clean_ts.split('.')[1]) > 6:
                clean_ts = clean_ts[:26] # Truncate to 6 decimal places
            
            # Re-add Z or parse as is
            # datetime.fromisoformat handles optional Z in 3.11+ but let's be safe with strptime
            # We normalized to YYYY-MM-DDTHH:MM:SS.mmmmmm
            if not clean_ts.endswith('Z'):
                 clean_ts += 'Z'
                 
            ts = datetime.strptime(clean_ts, '%Y-%m-%dT%H:%M:%S.%fZ')
            
            mid = c['mid']
            upsert_data.append({
                "market_symbol_id": market_symbol.id,
                "timeframe": timeframe,
                "timestamp": ts,
                "open": float(mid['o']),
                "high": float(mid['h']),
                "low": float(mid['l']),
                "close": float(mid['c']),
                "volume": int(c['volume']),
                "is_complete": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })

        if not upsert_data:
            return

        stmt = insert(Candle).values(upsert_data)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "updated_at": stmt.excluded.updated_at
            }
        )

        self.db.execute(upsert_stmt)
        self.db.commit()
        logger.info(f"Upserted {len(upsert_data)} candles for {symbol}")

def run_backfill_task(data_source_id: str, symbol: str, timeframe: str, count: int):
    """Background task wrapper."""
    # We need a fresh DB session for the background task
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not source:
            logger.error(f"DataSource {data_source_id} not found in background task")
            return
            
        service = OandaBackfillService(db, source)
        service.run(symbol, timeframe, count)
        
    except Exception as e:
        logger.error(f"Backfill Background Task Failed: {e}")
    finally:
        db.close()
