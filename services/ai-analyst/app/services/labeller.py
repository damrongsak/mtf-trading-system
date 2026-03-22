import logging
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.candle import Candle
from app.models.trade import Trade
from app.indicators.smc import detect_liquidity_sweeps, calculate_displacement_velocity
import pandas as pd

logger = logging.getLogger(__name__)

class AutomatedLabeller:
    """
    Scans historical data to apply ground-truth labels for ML/Analysis.
    """
    
    async def label_historical_candles(self, session: AsyncSession, symbol: str, timeframe: str, limit: int = 1000):
        """
        Labels candles with 'ai_labels' and 'regime_tag' based on post-hoc analysis.
        """
        logger.info(f"Starting historical labelling for {symbol} {timeframe}...")
        
        # 1. Fetch candles
        stmt = select(Candle).where(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe
        ).order_by(Candle.timestamp.desc()).limit(limit)
        
        result = await session.execute(stmt)
        candles = result.scalars().all()
        
        if not candles:
            logger.warning("No candles found for labelling.")
            return
            
        # Reverse to chronological order for processing
        candles = list(reversed(candles))
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'timestamp': c.timestamp,
            'open': float(c.open),
            'high': float(c.high),
            'low': float(c.low),
            'close': float(c.close),
            'volume': float(c.volume) if c.volume else 0
        } for c in candles])
        df.set_index('timestamp', inplace=True)
        
        # 2. Run analysis
        sweeps = detect_liquidity_sweeps(df)
        v_d = calculate_displacement_velocity(df)
        
        # 3. Apply labels
        # A sweep followed by a quick reversal is a 'valid_sweep'
        # A sweep followed by continued expansion is a 'fake_sweep'
        
        updates = []
        for sweep in sweeps:
            idx = sweep['index']
            # Look ahead 3 candles (post-hoc labels)
            if idx + 3 >= len(df):
                continue
                
            current_close = df['close'].iloc[idx]
            future_close_3 = df['close'].iloc[idx + 3]
            
            label = "unknown_sweep"
            if sweep['type'] == 'bullish_sweep':
                if future_close_3 > current_close:
                    label = "valid_bullish_sweep"
                else:
                    label = "fake_bullish_sweep"
            elif sweep['type'] == 'bearish_sweep':
                if future_close_3 < current_close:
                    label = "valid_bearish_sweep"
                else:
                    label = "fake_bearish_sweep"
                    
            # Map back to SQLAlchemy model
            candle_to_update = candles[idx]
            ai_labels = candle_to_update.ai_labels or {}
            ai_labels['sweep_type'] = label
            ai_labels['v_d_at_sweep'] = float(v_d.iloc[idx])
            
            candle_to_update.ai_labels = ai_labels
            updates.append(candle_to_update)
            
        if updates:
            await session.commit()
            logger.info(f"Successfully labelled {len(updates)} candles for {symbol}.")
            
    async def audit_labels(self, session: AsyncSession, threshold: float = 0.8):
        """
        Placeholder for manual audit or reinforcement learning confirmation.
        """
        pass

# Singleton
labeller = AutomatedLabeller()
