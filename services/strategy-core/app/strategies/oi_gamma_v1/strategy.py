import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any

from app.analysis.liquidity_profile import LiquidityProfileAnalyzer, GammaLevel
from app.models.open_interest import OpenInterest
from app.database import SessionLocal
from app.logic import SignalDirection

logger = logging.getLogger(__name__)

METADATA = {
    "name": "OI Gamma Heatmap Strategy",
    "description": "Trades based on Gamma Walls and Flips using Options Open Interest",
    "defaults": {
        "timeframe": "1h",
        "lookback_days": 7
    }
}

def fetch_latest_oi_snapshot() -> Optional[Dict[str, Any]]:
    """
    Helper to fetch the latest OI snapshot from DB.
    Returns a list of records for the analyzer.
    """
    db = SessionLocal()
    try:
        # 1. Get latest snapshot time
        latest_snapshot = db.query(OpenInterest.snapshot_at).order_by(OpenInterest.snapshot_at.desc()).first()
        
        if not latest_snapshot:
            return None
            
        snapshot_time = latest_snapshot[0]
        
        # 2. Get records
        records = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_time).all()
        
        if not records:
            return None
            
        # 3. Convert to dicts
        data = []
        underlying_price = None
        for r in records:
            data.append({
                'strike': float(r.strike),
                'call_oi': float(r.call_oi or 0),
                'put_oi': float(r.put_oi or 0),
                'underlying_price': float(r.underlying_price) if r.underlying_price else None
            })
            if r.underlying_price and underlying_price is None:
                underlying_price = float(r.underlying_price)
                
        return {
            "records": data,
            "snapshot_at": snapshot_time,
            "underlying_futures_price": underlying_price
        }
    except Exception as e:
        logger.error(f"Error fetching OI snapshot: {e}")
        return None
    finally:
        db.close()

def fetch_historical_oi(start_date: datetime, end_date: datetime) -> Dict[datetime, Dict[str, Any]]:
    """
    Fetch historical OI snapshots within a date range.
    Returns: Dict[timestamp, {records: [], underlying_price: float}]
    """
    db = SessionLocal()
    try:
        # Optimize: Fetch only necessary columns? 
        # For now, fetch all OpenInterest records in range
        records = db.query(OpenInterest).filter(
            OpenInterest.snapshot_at >= start_date,
            OpenInterest.snapshot_at <= end_date
        ).all()
        
        # Group by snapshot_at
        grouped = {}
        for r in records:
            ts = r.snapshot_at
            if ts not in grouped:
                grouped[ts] = {'records': [], 'underlying_price': None}
            
            grouped[ts]['records'].append({
                'strike': float(r.strike),
                'call_oi': float(r.call_oi or 0),
                'put_oi': float(r.put_oi or 0),
                'underlying_price': float(r.underlying_price) if r.underlying_price else None
            })
            if r.underlying_price and grouped[ts]['underlying_price'] is None:
                grouped[ts]['underlying_price'] = float(r.underlying_price)
                
        return grouped
    except Exception as e:
        logger.error(f"Error fetching historical OI: {e}")
        return {}
    finally:
        db.close()

def strategy_vectorized(candles_df: pd.DataFrame, oi_history: Optional[Dict[datetime, Any]] = None, params: dict = None):
    """
    Vectorized version of the strategy for backtesting.
    """
    if params is None: 
        params = {}
    
    entries = pd.Series(False, index=candles_df.index)
    exits = pd.Series(False, index=candles_df.index)
    
    if not oi_history:
        logger.warning("No OI History provided for OIGammaStrategy backtest.")
        return entries, exits

    analyzer = LiquidityProfileAnalyzer()
    
    # Sort OI timestamps
    oi_timestamps = sorted(oi_history.keys())
    
    # Optimize: Pre-calculate levels for all snapshots?
    # Or just iterate candles and find closest previous snapshot.
    
    # Iteration (Slow but flexible)
    # For backtesting 1 year of H1 (6000 candles), it's doable.
    
    last_levels = None
    last_regime = None
    last_gamma_flip = None
    last_snapshot_ts = None
    
    # Convert OI timestamps to Index for searchsorted
    oi_ts_index = pd.to_datetime(oi_timestamps).sort_values()

    for i in range(1, len(candles_df)):
        timestamp = candles_df.index[i]
        current_price = candles_df['close'].iloc[i]
        prev_close = candles_df['close'].iloc[i-1]
        
        # Find latest snapshot before current timestamp
        # Using searchsorted to find insertion point
        idx = oi_ts_index.searchsorted(timestamp) - 1
        
        if idx >= 0:
            snapshot_ts = oi_timestamps[idx]
            
            # Recalc if snapshot changed
            if snapshot_ts != last_snapshot_ts:
                snapshot_data = oi_history[snapshot_ts]
                # Analyze wrapper
                # We need to map current_price (Spot) to Futures if used?
                # The analyzer uses 'current_spot_price' to align strikes.
                # In backtest, 'current_price' IS the spot price at that time.
                analysis = analyzer.analyze_snapshot(snapshot_data['records'], current_spot_price=current_price)
                
                last_levels = analysis['levels']
                last_regime = analysis['regime'].regime
                last_gamma_flip = analysis['regime'].gamma_flip_level
                last_snapshot_ts = snapshot_ts

            if last_levels:
                # --- Logic (Same as strategy()) ---
                threshold = current_price * 0.001
                call_wall = next((l for l in last_levels if l.type == 'CALL_WALL'), None)
                put_wall = next((l for l in last_levels if l.type == 'PUT_WALL'), None)
                
                # POSITIVE GAMMA
                if last_regime == 'POSITIVE_GAMMA':
                    if put_wall and abs(current_price - put_wall.strike) < threshold:
                        entries.iloc[i] = True
                    elif call_wall and abs(current_price - call_wall.strike) < threshold:
                        exits.iloc[i] = True # Sell/Short
                        
                # NEGATIVE GAMMA
                elif last_regime == 'NEGATIVE_GAMMA':
                    if last_gamma_flip:
                         # Bullish Flip
                        if prev_close < last_gamma_flip and current_price > last_gamma_flip:
                             entries.iloc[i] = True
                        # Bearish Flip
                        elif prev_close > last_gamma_flip and current_price < last_gamma_flip:
                             exits.iloc[i] = True

    return entries, exits


async def strategy(state, data_manager):
    """
    OI Gamma Strategy:
    1. Fetch latest Spot Price (from data_manager)
    2. Fetch latest OI Snapshot (from DB)
    3. Analyze Liquidity Profile (Gamma Walls, Flip)
    4. Generate Signals based on proximity to levels or flip crossovers.
    """
    symbol = state.symbol
    # data_manager.get_data(symbol) returns a DataFrame with 'close', 'high', 'low', 'open'
    # index is datetime
    data = data_manager.get_data(symbol)

    if data.empty or len(data) < 20:
        return None, None, None
        
    current_price = data['close'].iloc[-1]
    
    # 1. Fetch OI Data
    # Note: This is a synchronous DB call. In a high-freq async loop, this should be offloaded.
    # But for a strategy tick (every few seconds/minutes), it's acceptable.
    oi_data = fetch_latest_oi_snapshot()
    
    if not oi_data:
        # No OI data, cannot trade this strategy
        return None, None, None
        
    # 2. Analyze
    analyzer = LiquidityProfileAnalyzer()
    
    # We use the futures underlying price for the offset calculation if available
    # But for the *Regime* and *Levels*, we need them mapped to SPOT.
    # The analyzer does the mapping if we provide the current spot price.
    # Wait, analyzer.analyze_snapshot takes 'current_spot_price'.
    # It calculates levels relative to Spot using the Offset.
    
    # Correct Usage:
    # We pass the Raw Futures Strikes (in records).
    # We pass the Current Spot Price.
    # The Analyzer needs to know the Futures Price to calc offset. 
    # The records contain 'underlying_price' (Futures Price).
    # Analyzer internal logic:
    #   offset = futures_price - spot_price
    #   adjusted_strike = raw_strike - offset
    analysis = analyzer.analyze_snapshot(oi_data['records'], current_spot_price=current_price)
    
    levels = analysis['levels']
    regime_info = analysis['regime']
    regime = regime_info.regime # "POSITIVE_GAMMA" | "NEGATIVE_GAMMA"
    gamma_flip = regime_info.gamma_flip_level
    
    # 3. Logic
    entries = pd.Series(False, index=data.index)
    exits = pd.Series(False, index=data.index)
    signal_dict = None
    
    # Define Proximity Threshold (e.g., 0.1% or 0.2%)
    # For Gold (2000), 0.1% is $2.
    threshold = current_price * 0.001 
    
    # Find Major Walls
    call_wall = next((l for l in levels if l.type == 'CALL_WALL'), None)
    put_wall = next((l for l in levels if l.type == 'PUT_WALL'), None)
    
    direction = None
    reason = ""
    stop_loss = 0.0
    target_price = 0.0
    
    # --- SCENARIO A: POSITIVE GAMMA (Mean Reversion) ---
    if regime == 'POSITIVE_GAMMA':
        # Buy at Put Wall (Support)
        if put_wall and abs(current_price - put_wall.strike) < threshold:
            direction = "BULLISH"
            reason = f"Positive Gamma: Bounce off Put Wall at {put_wall.strike}"
            stop_loss = put_wall.strike - (threshold * 2) # SL below wall
            target_price = current_price + (threshold * 10) # Simple target or next level
            # If Gamma Flip is above, target it
            if gamma_flip and gamma_flip > current_price:
                target_price = gamma_flip
                
        # Sell at Call Wall (Resistance)
        elif call_wall and abs(current_price - call_wall.strike) < threshold:
            direction = "BEARISH"
            reason = f"Positive Gamma: Reject off Call Wall at {call_wall.strike}"
            stop_loss = call_wall.strike + (threshold * 2)
            target_price = current_price - (threshold * 10)
            if gamma_flip and gamma_flip < current_price:
                target_price = gamma_flip

    # --- SCENARIO B: NEGATIVE GAMMA (Trend/Breakout) ---
    elif regime == 'NEGATIVE_GAMMA':
        # Check for Gamma Flip Crossover (Trend Change)
        # Verify if price JUST crossed the flip level?
        # We need previous close.
        if len(data) > 1 and gamma_flip:
            prev_close = data['close'].iloc[-2]
            
            # Bullish Flip: Price crossed ABOVE Gamma Flip
            if prev_close < gamma_flip and current_price > gamma_flip:
                direction = "BULLISH"
                reason = f"Gamma Flip Breakout (Bullish) at {gamma_flip}"
                stop_loss = gamma_flip - threshold
                target_price = call_wall.strike if call_wall else (current_price * 1.01)
                
            # Bearish Flip: Price crossed BELOW Gamma Flip
            elif prev_close > gamma_flip and current_price < gamma_flip:
                direction = "BEARISH"
                reason = f"Gamma Flip Breakdown (Bearish) at {gamma_flip}"
                stop_loss = gamma_flip + threshold
                target_price = put_wall.strike if put_wall else (current_price * 0.99)
                
    # --- EXECUTE ---
    if direction:
        # Check RRR (Optional)
        # rrr = abs(target_price - current_price) / abs(current_price - stop_loss)
        # if rrr < 1.0: return None, None, None
        
        if direction == "BULLISH":
            entries.iloc[-1] = True
        else:
            exits.iloc[-1] = True # Mapping Short to Exits for now (or separate signal)
            
        signal_dict = {
            "direction": direction,
            "stop_loss": stop_loss,
            "take_profit": target_price,
            "target_price": target_price,
            "reason": reason,
            "metadata": {
                "regime": regime,
                "gamma_flip": gamma_flip,
                "put_wall": put_wall.strike if put_wall else None,
                "call_wall": call_wall.strike if call_wall else None,
                "underlying_futures": oi_data.get('underlying_futures_price')
            }
        }
        
    return entries, exits, signal_dict
