import asyncio
import logging
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.models.candle import Candle
from app.adapters.binance import BinanceClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BinanceBackfill")

def get_binance_symbol(symbol: str) -> str:
    # Convert system symbol to Binance format (e.g., BTC_USD -> BTCUSDT if needed)
    sym = symbol.replace("/", "").replace("_", "")
    if sym in ["BTCUSD", "XBTUSD"]: return "BTCUSDT"
    if sym in ["ETHUSD"]: return "ETHUSDT"
    return sym

async def backfill_binance(days: int = 30):
    db = SessionLocal()
    from app.models.market import MarketCategory
    try:
        ds = db.query(DataSource).filter(DataSource.name == "BINANCE").first()
        if not ds:
            logger.info("Creating BINANCE Data Source...")
            ds = DataSource(name="BINANCE", provider="BINANCE", type="api", config_json={})
            db.add(ds)
            db.commit()

        cat = db.query(MarketCategory).filter(MarketCategory.name == "Crypto").first()
        if not cat:
            cat = MarketCategory(name="Crypto", order_index=2)
            db.add(cat)
            db.commit()

        # Target only BTCUSDT and ETHUSDT
        target_symbols = ["BTCUSDT", "ETHUSDT"]
        filtered_symbols = []
        for sym in target_symbols:
            ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == sym).first()
            if not ms:
                logger.info(f"Creating MarketSymbol for {sym}")
                ms = MarketSymbol(
                    category_id=cat.id,
                    data_source_id=ds.id,
                    symbol=sym,
                    display_name=sym,
                    is_active=True,
                    details={"baseAsset": sym[:-4] if sym.endswith("USDT") else sym, "quoteAsset": "USDT"}
                )
                db.add(ms)
                db.commit()
            filtered_symbols.append(ms)

        client = BinanceClient()
        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        start_ts = int(start_date.timestamp() * 1000)

        for ms in filtered_symbols:
            binance_sym = get_binance_symbol(ms.symbol)
            if binance_sym not in ["BTCUSDT", "ETHUSDT"]:
                logger.info(f"Skipping {ms.symbol} as per strict restriction to BTCUSDT, ETHUSDT spot.")
                continue
                
            logger.info(f"Processing Binance symbol: {ms.symbol} (Mapped to {binance_sym})")
            
            for tf in timeframes:
                logger.info(f"  Timeframe: {tf}")
                current_to_ts = int(end_date.timestamp() * 1000)
                total_saved = 0
                chunk_count = 0
                
                while current_to_ts > start_ts and chunk_count < 100:
                    chunk_count += 1
                    try:
                        raw_candles = client.fetch_candles(
                            symbol=binance_sym,
                            timeframe=tf,
                            count=1000,
                            end_time=current_to_ts
                        )
                        
                        if not raw_candles:
                            logger.info("    No more candles found.")
                            break
                            
                        candles_to_save = []
                        earliest_ts = current_to_ts
                        
                        for c in raw_candles:
                            open_time = c[0]
                            if open_time < earliest_ts:
                                earliest_ts = open_time
                            
                            if open_time < start_ts:
                                continue
                                
                            ts = datetime.fromtimestamp(open_time / 1000.0, tz=timezone.utc)
                            
                            candles_to_save.append({
                                "market_symbol_id": ms.id,
                                "symbol": ms.symbol,
                                "timeframe": tf,
                                "timestamp": ts,
                                "open": float(c[1]),
                                "high": float(c[2]),
                                "low": float(c[3]),
                                "close": float(c[4]),
                                "volume": float(c[5]),
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
                            total_saved += count
                            logger.info(f"    Saved {count} candles. Total: {total_saved}. Earliest: {datetime.fromtimestamp(earliest_ts/1000, tz=timezone.utc)}")
                            
                        if earliest_ts >= current_to_ts:
                            break
                        current_to_ts = earliest_ts - 1
                        
                        if len(raw_candles) < 500: # chunk smaller than limit implies end
                            break
                            
                    except Exception as e:
                        logger.error(f"    Error fetching Binance candles: {e}")
                        time.sleep(5)
                        break

                logger.info(f"  Finished {ms.symbol} {tf}. Total saved: {total_saved}")

    except Exception as e:
        logger.error(f"Global Binance Backfill Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(backfill_binance(days=args.days))
