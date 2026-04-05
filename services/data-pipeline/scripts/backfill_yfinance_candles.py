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

async def backfill_yfinance(days: int = 365, target_timeframes: list = None, target_symbols: list = None):
    db = SessionLocal()
    from app.models.data_source import DataSource
    try:
        # 1. Find YAHOO_FINANCE Data Source
        ds = db.query(DataSource).filter(DataSource.provider == "YAHOO_FINANCE", DataSource.is_active == True).first()
        if not ds:
            logger.error("YAHOO_FINANCE Data source not found or inactive.")
            return

        # 2. Get Active YAHOO_FINANCE Symbols
        query = db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == ds.id, 
            MarketSymbol.is_active == True
        )
        if target_symbols:
            query = query.filter(MarketSymbol.symbol.in_(target_symbols))
            
        active_symbols = query.all()

        if not active_symbols:
            logger.warning("No active YAHOO_FINANCE symbols found matching criteria.")
            return

        # 3. Timeframe Setup
        all_timeframes_map = {
            "M15": "15m", 
            "H1": "1h", 
            "H4": "1h", # Yahoo has no native 4h, using 1h for resampling if needed (though script currently just pulls)
            "D1": "1d", 
            "W1": "1wk", 
            "MN1": "1mo"
        }
        tfs_to_process = target_timeframes if target_timeframes else list(all_timeframes_map.keys())
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        for ms in active_symbols:
            yf_ticker = ms.details.get("yfinance_ticker")
            if not yf_ticker:
                logger.warning(f"Missing yfinance_ticker in details for {ms.symbol}. Skipping.")
                continue
                
            logger.info(f"Processing YFinance symbol: {ms.symbol} (Ticker: {yf_ticker})")
            ticker = yf.Ticker(yf_ticker)
            
            for tf_sys in tfs_to_process:
                tf_yf = all_timeframes_map.get(tf_sys)
                if not tf_yf:
                    logger.warning(f"  Skipping invalid timeframe: {tf_sys}")
                    continue
                    
                logger.info(f"  Timeframe: {tf_sys} (Mapping: {tf_yf})")
                try:
                    # Intraday limits: Yahoo usually limits 15m to 60 days
                    if tf_sys == "M15" and days > 60:
                        period_str = "60d"
                    else:
                        period_str = f"{days}d" if days < 730 else "max"
                        
                    df = ticker.history(period=period_str, interval=tf_yf)
                    
                    if df.empty:
                        logger.warning(f"    No data found for {yf_ticker} at {tf_yf}")
                        continue
                        
                    logger.info(f"    Fetched {len(df)} rows for {yf_ticker}")
                    
                    candles_to_save = []
                    for timestamp_pd, row in df.iterrows():
                        ts = timestamp_pd.to_pydatetime()
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        else:
                            ts = ts.astimezone(timezone.utc)
                            
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
                        logger.info(f"    Saved {count} candles for {ms.symbol} {tf_sys}.")
                        
                except Exception as e:
                    logger.error(f"    Error processing {tf_sys} for {ms.symbol}: {e}")

    except Exception as e:
        logger.error(f"Global YFinance Backfill Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--timeframes", type=str, help="Comma separated timeframes (M15,H1,H4,D1)")
    parser.add_argument("--symbols", type=str, help="Comma separated symbols (VIX,GVZ,DXY)")
    args = parser.parse_args()
    
    tf_list = args.timeframes.split(',') if args.timeframes else None
    sym_list = args.symbols.split(',') if args.symbols else None
    
    asyncio.run(backfill_yfinance(days=args.days, target_timeframes=tf_list, target_symbols=sym_list))

