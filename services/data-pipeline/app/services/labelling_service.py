import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.candle import Candle
from app.repositories.candle_repository import CandleRepository
import redis
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

class LabellingService:
    """
    Automated AI Labelling Service for Price Data.
    Performs vectorized batch processing to identify market regimes and SMC patterns.
    High performance (O(N)) using Pandas and NumPy.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.candle_repo = CandleRepository(db)
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def run_labelling_job(self, batch_size: int = 1000):
        """
        Main entry point for the labelling job.
        Scans for candles that haven't been labelled yet.
        """
        logger.info(f"Starting AI Labelling Job (Batch Size: {batch_size})...")
        
        # 1. Implementation Note: To keep Big O low, we process per Symbol/Timeframe
        # Fetch symbols that need labelling
        try:
            # For simplicity in this iteration, we fetch symbols from the candles table directly
            # using a distinct query on rows where ai_labels IS NULL.
            distinct_symbols_tf = self.db.execute(
                "SELECT DISTINCT market_symbol_id, timeframe FROM candles WHERE ai_labels IS NULL OR regime_tag IS NULL LIMIT 10"
            ).fetchall()
            
            if not distinct_symbols_tf:
                logger.debug("No pending candles for labelling.")
                return

            for ms_id, tf in distinct_symbols_tf:
                await self.process_symbol_timeframe(ms_id, tf, limit=batch_size)
                
            logger.info("AI Labelling Job completed.")
        except Exception as e:
            logger.error(f"Labelling Job failed: {e}", exc_info=True)

    async def process_symbol_timeframe(self, ms_id: str, tf: str, limit: int = 1000):
        """Processes a specific symbol/timeframe batch."""
        logger.info(f"Labelling {ms_id} {tf}...")
        
        # 1. Fetch data into DataFrame
        # We need some context (previous candles) even if we only label the new ones
        # But for full vectorized calculation, we pull the batch + lookback
        lookback = 100
        candles = self.db.query(Candle).filter(
            Candle.market_symbol_id == ms_id,
            Candle.timeframe == tf
        ).order_by(Candle.timestamp.desc()).limit(limit + lookback).all()
        
        if not candles:
            return

        # Reverse to get chronological order
        candles = list(reversed(candles))
        
        df = pd.DataFrame([
            {
                "id": c.id,
                "timestamp": c.timestamp,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume or 0)
            }
            for c in candles
        ])
        
        if len(df) < 20:
            return

        # 2. Vectorized Calculations
        labels_df = self.calculate_labels(df)
        
        # 3. Update DB
        # Only update rows that were in the original 'limit' (excluding lookback buffer)
        # and that don't have labels yet (or we overwrite if needed).
        # For simplicity, we update based on index matches.
        
        update_count = 0
        for i, row in labels_df.iterrows():
            # Skip lookback buffer if it already had labels? 
            # Or just update everything to ensures consistency.
            candle_id = row['id']
            db_candle = self.db.query(Candle).get(candle_id)
            if db_candle:
                db_candle.ai_labels = row['ai_labels']
                db_candle.regime_tag = row['regime_tag']
                update_count += 1
        
        self.db.commit()
        
        # 4. Phase 63: Broadcast to Redis L3 Cache (ECST)
        if not labels_df.empty:
            await self.broadcast_to_redis(ms_id, tf, labels_df.iloc[-1])

        logger.info(f"Updated {update_count} candles for {ms_id} {tf}. Broadcasted latest to Redis.")

    async def broadcast_to_redis(self, ms_id: str, tf: str, latest_row: pd.Series):
        """
        Broadcasts the latest label to Redis for O(1) access by Execution/Strategy services.
        Redis Key: mtf:labels:{symbol}:{timeframe}
        """
        try:
            key = f"mtf:labels:{ms_id}:{tf}"
            data = {
                "timestamp": latest_row['timestamp'].isoformat() if hasattr(latest_row['timestamp'], 'isoformat') else str(latest_row['timestamp']),
                "regime": latest_row['regime_tag'],
                "patterns": latest_row['ai_labels'],
                "confidence": latest_row['ai_labels'].get("confidence", 0.5)
            }
            self.redis_client.set(key, json.dumps(data), ex=3600) # 1 hour TTL
            # Also publish to a stream/channel if needed for event-driven reactions
            self.redis_client.publish(f"mtf:events:labels:{ms_id}", json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to broadcast to Redis: {e}")

    def calculate_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates SMC and Regime labels using vectorized operations.
        Returns the original DataFrame with 'ai_labels' and 'regime_tag' columns.
        """
        df = df.copy()
        
        # --- 1. Regime Detection (Vectorized) ---
        # Displacement Velocity (V_d)
        body = (df['close'] - df['open']).abs()
        v_d = body / body.rolling(window=20).mean()
        v_d_rolling_mean = v_d.rolling(window=20).mean()
        v_d_rolling_std = v_d.rolling(window=20).std()
        
        # Regime tags: TRENDING, RANGING, EXPANDING
        df['regime_tag'] = "RANGING"
        df.loc[v_d > (v_d_rolling_mean + 1 * v_d_rolling_std), 'regime_tag'] = "TRENDING"
        df.loc[v_d > (v_d_rolling_mean + 3 * v_d_rolling_std), 'regime_tag'] = "EXPANDING" # Hyperbolic
        
        # --- 2. SMC Pattern Detection (Basic proxy for ai_labels) ---
        df['ai_labels'] = [{} for _ in range(len(df))]
        
        # Fair Value Gaps (FVG)
        high = df['high']
        low = df['low']
        
        bull_fvg = (low > high.shift(2))
        bear_fvg = (high < low.shift(2))
        
        # Liquidity Sweeps (recent high/low)
        window = 10
        recent_high = high.shift(1).rolling(window=window).max()
        recent_low = low.shift(1).rolling(window=window).min()
        
        bear_sweep = (high > recent_high) & (df['close'] < recent_high)
        bull_sweep = (low < recent_low) & (df['close'] > recent_low)

        # 3. Advanced SMC Patterns (Phase 63)
        # Order Blocks (OB) - Last opposite candle before displacement
        df['body'] = (df['close'] - df['open'])
        df['displacement'] = df['body'].abs() / df['body'].abs().rolling(window=20).mean()
        
        # Bullish OB: Last Red candle before a Green displacement that breaks local high
        bull_ob = (df['body'].shift(1) < 0) & (df['displacement'] > 2.0) & (df['close'] > df['high'].shift(2))
        # Bearish OB: Last Green candle before a Red displacement that breaks local low
        bear_ob = (df['body'].shift(1) > 0) & (df['displacement'] > 2.0) & (df['close'] < df['low'].shift(2))
        
        # Change of Character (ChoCh) - First break of counter-trend structure
        # Simplified: Break of 20-period high while regime was bearish
        df['choch_bull'] = (df['close'] > df['high'].shift(1).rolling(window=20).max()) & (df['regime_tag'].shift(1) == "RANGING")
        df['choch_bear'] = (df['close'] < df['low'].shift(1).rolling(window=20).min()) & (df['regime_tag'].shift(1) == "RANGING")

        # --- 4. Advanced Liquidity Matrix (Phase 64 - Hunter Mode) ---
        # A. Session Tracker (Asian Range: 00:00-08:00 UTC)
        df['hour'] = df['timestamp'].dt.hour
        is_asian = (df['hour'] >= 0) & (df['hour'] < 8)
        
        # We find the High/Low of the Asian session for each day
        df['date'] = df['timestamp'].dt.date
        asian_df = df[is_asian]
        asian_highs = asian_df.groupby('date')['high'].max().rename('asian_high')
        asian_lows = asian_df.groupby('date')['low'].min().rename('asian_low')
        
        df = df.merge(asian_highs, on='date', how='left')
        df = df.merge(asian_lows, on='date', how='left')
        
        # London Judas Swing (Fakeout) - Breaking Asian Range during London Open (08:00-09:30 UTC)
        is_london_open = (df['hour'] >= 8) & (df['hour'] < 10)
        df['judas_bull'] = is_london_open & (df['low'] < df['asian_low']) & (df['close'] > df['asian_low'])
        df['judas_bear'] = is_london_open & (df['high'] > df['asian_high']) & (df['close'] < df['asian_high'])
        
        # B. Structural Landmarks (PDH / PDL)
        daily_highs = df.groupby('date')['high'].max().shift(1).rename('pdh')
        daily_lows = df.groupby('date')['low'].min().shift(1).rename('pdl')
        df = df.merge(daily_highs, on='date', how='left')
        df = df.merge(daily_lows, on='date', how='left')
        
        # C. Equal Highs/Lows (EQH / EQL) - Retail Double Top/Bottom
        # Proximity threshold: 5 pips (approx 0.0005 for Forex, 0.5 for Gold)
        # Using a 0.02% threshold as a proxy for cross-asset
        threshold = df['close'] * 0.0002 
        df['is_eqh'] = (df['high'] - df['high'].shift(1)).abs() < threshold
        df['is_eql'] = (df['low'] - df['low'].shift(1)).abs() < threshold
        
        # D. Psychological Round Numbers (.00, .50)
        df['is_round_number'] = (df['close'] % 50 < 2) | (df['close'] % 50 > 48) # Proxy for proximity

        # Apply labels and Confidence Scoring
        for idx in range(len(df)):
            if bull_fvg.iloc[idx]:
                df.at[idx, 'ai_labels']['fvg'] = "bullish"
                df.at[idx, 'ai_labels']['fvg_size'] = float(low.iloc[idx] - high.iloc[idx-2])
            if bear_fvg.iloc[idx]:
                df.at[idx, 'ai_labels']['fvg'] = "bearish"
                df.at[idx, 'ai_labels']['fvg_size'] = float(low.iloc[idx-2] - high.iloc[idx])
            if bear_sweep.iloc[idx]:
                df.at[idx, 'ai_labels']['sweep'] = "bearish"
            if bull_sweep.iloc[idx]:
                df.at[idx, 'ai_labels']['sweep'] = "bullish"
            if bull_ob.iloc[idx]:
                df.at[idx, 'ai_labels']['ob'] = "bullish"
            if bear_ob.iloc[idx]:
                df.at[idx, 'ai_labels']['ob'] = "bearish"
            if df.at[idx, 'choch_bull']:
                df.at[idx, 'ai_labels']['choch'] = "bullish"
            if df.at[idx, 'choch_bear']:
                df.at[idx, 'ai_labels']['choch'] = "bearish"

            # --- Phase 64: Advanced Liquidity Labels ---
            if df.at[idx, 'judas_bull']:
                df.at[idx, 'ai_labels']['judas'] = "bullish"
            if df.at[idx, 'judas_bear']:
                df.at[idx, 'ai_labels']['judas'] = "bearish"
            if not pd.isna(df.at[idx, 'asian_high']):
                df.at[idx, 'ai_labels']['asian_range'] = {"high": float(df.at[idx, 'asian_high']), "low": float(df.at[idx, 'asian_low'])}
            if not pd.isna(df.at[idx, 'pdh']):
                df.at[idx, 'ai_labels']['prev_day'] = {"pdh": float(df.at[idx, 'pdh']), "pdl": float(df.at[idx, 'pdl'])}
            if df.at[idx, 'is_eqh']: df.at[idx, 'ai_labels']['eqh'] = True
            if df.at[idx, 'is_eql']: df.at[idx, 'ai_labels']['eql'] = True
            if df.at[idx, 'is_round_number']: df.at[idx, 'ai_labels']['psych_level'] = True

            # Confidence Scoring (0.0 to 1.0)
            # Base 0.5, +0.2 for Confluence, +0.1 for Volatility alignment
            conf = 0.5
            confluences = len(df.at[idx, 'ai_labels'])
            if confluences > 1: conf += 0.2
            if df.at[idx, 'regime_tag'] == "TRENDING": conf += 0.1
            if df.at[idx, 'displacement'] > 2.5: conf += 0.1
            
            df.at[idx, 'ai_labels']['confidence'] = min(round(conf, 2), 1.0)
            df.at[idx, 'ai_labels']['volatility_score'] = round(float(v_d.iloc[idx]), 2) if not np.isnan(v_d.iloc[idx]) else 1.0
        
        return df
