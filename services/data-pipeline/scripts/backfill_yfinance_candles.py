import asyncio
import logging
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import yfinance as yf

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.market import MarketSymbol, MarketCategory
from app.models.candle import Candle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("YFinanceBackfill")

# Combined mappings for Macro and Trading symbols
YAHOO_MAPPINGS = {
    # Macro / Indices
    "^VIX": "VIX",
    "^GVZ": "GVZ",
    "DX-Y.NYB": "DXY",
    "^GSPC": "SPX",
    "TIP": "TIPS",
    # Gold & FX (Spot)
    "GC=F": "GC_FUTURES",
    "XAUUSD=X": "XAUUSD_SPOT",
    "GBPUSD=X": "GBPUSD",
    "USDJPY=X": "USDJPY"
}

def find_market_symbol(db: Session, sys_sym: str) -> list:
    """Finds all MarketSymbol records matching the system symbol (ignoring underscores)."""
    # Try exact match first
    results = db.query(MarketSymbol).filter(MarketSymbol.symbol == sys_sym).all()
    if results:
        return results
        
    # Try with underscore (e.g., XAU_USD)
    with_underscore = sys_sym[:3] + "_" + sys_sym[3:] if len(sys_sym) == 6 else sys_sym
    results = db.query(MarketSymbol).filter(MarketSymbol.symbol == with_underscore).all()
    if results:
        return results
        
    # Try case-insensitive search
    results = db.query(MarketSymbol).filter(MarketSymbol.symbol.ilike(f"%{sys_sym}%")).all()
    return results

def backfill_yfinance(days: int = 365):
    db = SessionLocal()
    try:
        # Added M15 and H4 support
        timeframes = {"M15": "15m", "H1": "1h", "H4": "1h", "D1": "1d", "W1": "1wk"}
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        for yf_sym, sys_sym in YAHOO_MAPPINGS.items():
            logger.info(f"Processing YFinance symbol: {yf_sym} -> {sys_sym}")
            
            # Find matching symbols in DB (could be multiple brokers)
            market_symbols = find_market_symbol(db, sys_sym)
            
            if not market_symbols:
                # If it's a Macro symbol, create it
                if sys_sym in ["VIX", "GVZ", "DXY", "SPX", "TIPS"]:
                    logger.info(f"Creating missing symbol for macro: {sys_sym}")
                    
                    # Find Yahoo Data Source
                    from app.models.market import DataSource
                    ds = db.query(DataSource).filter(DataSource.provider == "YAHOO_FINANCE").first()
                    ds_id = ds.id if ds else None
                    
                    cat = db.query(MarketCategory).filter(MarketCategory.name == "Macro").first()
                    if not cat:
                        cat = MarketCategory(name="Macro", order_index=99)
                        db.add(cat)
                        db.commit()
                        
                    ms = MarketSymbol(
                        category_id=cat.id,
                        symbol=sys_sym,
                        display_name=sys_sym,
                        data_source_id=ds_id,
                        details={"yfinance_ticker": yf_sym, "asset_class": "Macro"}
                    )
                    db.add(ms)
                    db.commit()
                    market_symbols = [ms]
                else:
                    logger.warning(f"No MarketSymbol found for {sys_sym}. Skipping.")
                    continue

            for ms in market_symbols:
                logger.info(f"  Backfilling {ms.symbol} (ID: {ms.id})")
                for tf_sys, tf_yf in timeframes.items():
                    logger.info(f"    Fetching {tf_sys} ({tf_yf}) for past {days} days")
                    try:
                        ticker = yf.Ticker(yf_sym)
                        # Adjustment for intraday limits (Yahoo limits 15m to last 60 days usually)
                        if tf_sys == "M15":
                            period_str = "60d"
                        else:
                            period_str = f"{days}d" if days < 730 else "max"
                            
                        df = ticker.history(period=period_str, interval=tf_yf)
                        
                        if df.empty:
                            logger.warning(f"    No data for {yf_sym} at {tf_yf}")
                            continue
                        
                        logger.info(f"    Fetched {len(df)} rows for {yf_sym} at {tf_yf}")
                        candles_to_save = []
                        # Deduplicate by timestamp
                        unique_rows = {}
                        for timestamp_pd, row in df.iterrows():
                            ts = timestamp_pd.to_pydatetime()
                            if ts.tzinfo is None:
                                ts = ts.replace(tzinfo=timezone.utc)
                            else:
                                ts = ts.astimezone(timezone.utc)
                            
                            unique_rows[ts] = row
                            
                        for ts, row in unique_rows.items():
                            if ts < start_date:
                                continue
                                
                            candles_to_save.append({
                                "market_symbol_id": ms.id,
                                "symbol": ms.symbol,
                                "timeframe": tf_sys,
                                "timestamp": ts,
                                "open": float(row['Open']),
                                "high": float(row['High']),
                                "low": float(row['Low']),
                                "close": float(row['Close']),
                                "volume": float(row['Volume']),
                                "is_complete": True
                            })
                            
                        if candles_to_save:
                            count = 0
                            for c_data in candles_to_save:
                                existing = db.query(Candle).filter(
                                    Candle.market_symbol_id == c_data['market_symbol_id'],
                                    Candle.timeframe == c_data['timeframe'],
                                    Candle.timestamp == c_data['timestamp']
                                ).first()
                                
                                if existing:
                                    existing.open = c_data['open']
                                    existing.high = c_data['high']
                                    existing.low = c_data['low']
                                    existing.close = c_data['close']
                                    existing.volume = c_data['volume']
                                else:
                                    db.add(Candle(**c_data))
                                count += 1
                            
                            db.commit()
                            logger.info(f"      Saved {count} candles for {ms.symbol} {tf_sys}.")

                    except Exception as e:
                        logger.error(f"    Error fetching {yf_sym} for {ms.symbol}: {e}")

    except Exception as e:
        logger.error(f"Global YFinance Backfill Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()
    backfill_yfinance(days=args.days)

