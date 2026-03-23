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

MACRO_SYMBOLS = {
    "^VIX": "VIX",
    "^GVZ": "GVZ",
    "DX-Y.NYB": "DXY",
    "^GSPC": "SPX",
    "TIP": "TIPS"
}

def backfill_yfinance(days: int = 365):
    db = SessionLocal()
    try:
        timeframes = {"D1": "1d", "W1": "1wk"}
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        for yf_sym, sys_sym in MACRO_SYMBOLS.items():
            logger.info(f"Processing YFinance symbol: {yf_sym} -> {sys_sym}")
            
            # Categories and Symbols Management
            cat = db.query(MarketCategory).filter(MarketCategory.name == "Macro").first()
            if not cat:
                logger.info("Creating 'Macro' MarketCategory...")
                cat = MarketCategory(name="Macro", order_index=99)
                db.add(cat)
                db.commit()

            ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == sys_sym).first()
            if not ms:
                logger.info(f"Creating missing symbol for macro: {sys_sym}")
                ms = MarketSymbol(
                    category_id=cat.id,
                    symbol=sys_sym,
                    display_name=sys_sym,
                    details={"yfinance_ticker": yf_sym, "asset_class": "Macro"}
                )
                db.add(ms)
                db.commit()

            for tf_sys, tf_yf in timeframes.items():
                logger.info(f"  Fetching {tf_sys} ({tf_yf}) for past {days} days")
                try:
                    ticker = yf.Ticker(yf_sym)
                    period_str = f"{days}d" if days < 730 else "max"
                    df = ticker.history(period=period_str, interval=tf_yf)
                    
                    if df.empty:
                        logger.warning(f"  No data for {yf_sym} at {tf_yf}")
                        continue
                    
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
                        logger.info(f"    Saved {count} candles for {sys_sym} {tf_sys}.")

                except Exception as e:
                    logger.error(f"  Error fetching {yf_sym}: {e}")

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
