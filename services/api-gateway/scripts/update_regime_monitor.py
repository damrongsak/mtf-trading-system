import sys
import os
import logging
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")
SYMBOL = "XAUUSD"
TIMEFRAME = "H4"
MAX_DTE = 60 # Rule 5.6.2: Institutional Monitor Mode Focus

def update_regime_monitor():
    """
    Core pipeline to aggregate GEX regime metrics onto the H4 timeframe.
    Implements Rule 5.6 (Institutional CME Heatmap/DTE 60-day aggregation).
    """
    logger.info(f"Starting Regime Monitor Pipeline for {SYMBOL} ({TIMEFRAME})")
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Fetch H4 Candles
        logger.info(f"Fetching {TIMEFRAME} candles...")
        candles_query = text("""
            SELECT timestamp, close 
            FROM candles 
            WHERE symbol = :symbol AND timeframe = :timeframe
            ORDER BY timestamp ASC
        """)
        candles_df = pd.read_sql(candles_query, engine, params={"symbol": SYMBOL, "timeframe": TIMEFRAME})
        
        if candles_df.empty:
            logger.error("No candles found. Ensure data pipeline is running.")
            return

        # 2. Fetch OI Snapshots
        logger.info(f"Fetching OI snapshots (DTE <= {MAX_DTE})...")
        oi_query = text("""
            SELECT snapshot_at, strike, call_oi, put_oi, underlying_price
            FROM open_interest
            WHERE dte <= :max_dte
            ORDER BY snapshot_at ASC, strike ASC
        """)
        oi_df = pd.read_sql(oi_query, engine, params={"max_dte": MAX_DTE})
        
        if oi_df.empty:
            logger.error("No Open Interest data found.")
            return

        # 3. Calculate Aggregated GEX per snapshot
        # For simplicity, we calculate a net GEX proxy per snapshot
        # Institutional Standard (V2.5) requires strike level analysis
        # Total GEX proxy: sum((call_oi - put_oi) * underlying_price) -> Simplified Net GEX
        # Real GEX involves Black-Scholes, but for the monitor, Net OI * Price is a valid proxy for scaling
        
        oi_df['net_oi'] = oi_df['call_oi'] - oi_df['put_oi']
        oi_df['gex_proxy'] = oi_df['net_oi'] * oi_df['underlying_price'].astype(float)
        
        snapshot_summary = oi_df.groupby('snapshot_at').agg({
            'gex_proxy': 'sum',
            'underlying_price': 'mean'
        }).reset_index()
        
        # 4. Forward-Fill Merge onto H4 Candles (Rule 5.6.3)
        # We want the most recent snapshot for each candle
        snapshot_summary = snapshot_summary.sort_values('snapshot_at')
        candles_df = candles_df.sort_values('timestamp')
        
        # it finds the last observation at or before the candle timestamp
        snapshot_summary['snapshot_at'] = pd.to_datetime(snapshot_summary['snapshot_at'], utc=True)
        candles_df['timestamp'] = pd.to_datetime(candles_df['timestamp'], utc=True)
        
        merged_df = pd.merge_asof(
            candles_df, 
            snapshot_summary, 
            left_on='timestamp', 
            right_on='snapshot_at', 
            direction='backward'
        )
        
        # 5. Store / Alert (Rule 5.6.3: Institutional Mapping)
        if not merged_df.empty:
            # We only care about the latest N records to avoid massive batch inserts if run frequently
            # But for the first run, we might want to backfill. 
            # Let's take the last 100 H4 candles to ensure continuity.
            recent_df = merged_df.tail(100).copy()
            
            logger.info(f"Upserting {len(recent_df)} regime records to DB...")
            
            for _, row in recent_df.iterrows():
                if pd.isna(row['gex_proxy']):
                    continue
                    
                regime_type = 'POSITIVE_GAMMA' if row['gex_proxy'] > 0 else 'NEGATIVE_GAMMA'
                is_noise = abs(row['gex_proxy']) < 1000000 # Institutional Noise Floor
                
                # Upsert Logic
                upsert_query = text("""
                    INSERT INTO regime_monitor (symbol, timeframe, timestamp, gex_proxy, underlying_price, regime_type, is_noise, metadata)
                    VALUES (:symbol, :timeframe, :timestamp, :gex_proxy, :underlying_price, :regime_type, :is_noise, :metadata)
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        gex_proxy = EXCLUDED.gex_proxy,
                        underlying_price = EXCLUDED.underlying_price,
                        regime_type = EXCLUDED.regime_type,
                        is_noise = EXCLUDED.is_noise,
                        metadata = EXCLUDED.metadata
                """)
                
                session.execute(upsert_query, {
                    "symbol": SYMBOL,
                    "timeframe": TIMEFRAME,
                    "timestamp": row['timestamp'],
                    "gex_proxy": row['gex_proxy'],
                    "underlying_price": row['underlying_price'],
                    "regime_type": regime_type,
                    "is_noise": is_noise,
                    "metadata": json.dumps({
                        "source": "InstitutionalRegimeMonitor_V2.5",
                        "snapshot_at": row['snapshot_at'].isoformat() if pd.notna(row['snapshot_at']) else None
                    })
                })
            
            session.commit()
            
            latest = recent_df.iloc[-1]
            logger.info(f"Current Regime: {latest['timestamp']} | GEX Proxy: {latest['gex_proxy']:.2f} | Status: {'NOISE' if abs(latest['gex_proxy']) < 1000000 else regime_type}")
        
        logger.info("Regime Monitor Update Complete.")

    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    update_regime_monitor()
