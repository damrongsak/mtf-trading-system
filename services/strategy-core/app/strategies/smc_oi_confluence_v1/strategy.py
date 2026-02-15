import logging
# import pandas as pd # Moved inside strategy function
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.analysis.liquidity_profile import LiquidityProfileAnalyzer
from app.models.open_interest import OpenInterest
from app.database import SessionLocal
from app.indicators.smc import analyze_smc

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Gold SMC + OI Confluence",
    "description": "Institutional Trap & Shift Strategy using CME Options OI Walls",
    "defaults": {
        "timeframe": "15m",
        "lookback_days": 30,
        "risk_per_trade": 0.01,
        "confluence_threshold": 0.001 # 0.1% price proximity
    }
}

def fetch_latest_oi_snapshot() -> Optional[Dict[str, Any]]:
    """
    Helper to fetch the latest OI snapshot from DB.
    """
    db = SessionLocal()
    try:
        latest_snapshot = db.query(OpenInterest.snapshot_at).order_by(OpenInterest.snapshot_at.desc()).first()
        if not latest_snapshot:
            return None
        
        snapshot_time = latest_snapshot[0]
        records = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_time).all()
        
        if not records:
            return None
            
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

async def strategy(state, data_manager):
    """
    Gold SMC + OI Confluence Strategy
    
    Phase A: Daily Structure (OI Walls)
    Phase B: Trap (Liquidity Sweep into Wall)
    Phase C: Shift (MSS after Sweep)
    Phase D: Entry (Limit at FVG/OB)
    """
    symbol = state.symbol
    data = data_manager.get_data(symbol) # Expecting M15 or M5 data

    if data.empty or len(data) < 50:
        return None, None, None

    current_price = data['close'].iloc[-1]
    timestamp = data.index[-1]

    # 1. Get OI Context (Daily)
    oi_data = fetch_latest_oi_snapshot()
    if not oi_data:
        return None, None, None # No OI Data, No Trade

    analyzer = LiquidityProfileAnalyzer()
    # We analyze OI relative to current price to find Walls
    analysis = analyzer.analyze_snapshot(oi_data['records'], current_spot_price=current_price)
    levels = analysis['levels']
    
    call_wall = next((l for l in levels if l.type == 'CALL_WALL'), None)
    put_wall = next((l for l in levels if l.type == 'PUT_WALL'), None)
    
    # 2. Get SMC Context (LTF Structure)
    # analyze_smc returns a dict with sweeps, structure, ob, fvg
    smc = analyze_smc(data, symbol)
    
    import pandas as pd
    entries = pd.Series(False, index=data.index)
    exits = pd.Series(False, index=data.index)
    signal_dict = None
    
    threshold = current_price * 0.001
    
    bias = "NEUTRAL"
    setup_phase = "WAITING"
    reason = ""
    
    # --- BULLISH SETUP ---
    # Condition 1: Identify Put Wall (Support)
    
    near_put_wall = False
    if put_wall and abs(current_price - put_wall.strike) < (current_price * 0.05):
        near_put_wall = True

        
    # Condition 2: Liquidity Sweep (Taking out lows) recently
    # Looking for a sweep that happened *into* the wall zone
    # Note: smc.py 'bullish_sweep' means sweeping a low and closing above (Bullish reaction)
    recent_sweeps = [s for s in smc['liquidity_sweeps'] if s['type'] == 'bullish_sweep' and s['index'] >= len(data) - 10]
    has_sweep = len(recent_sweeps) > 0
    

    
    valid_sweep = False
    if recent_sweeps and near_put_wall:
        # Check if any sweep touched the wall zone or happened comfortably near it
        for s in reversed(recent_sweeps):
             sweep_price = s['price']
             # If sweep low is within tolerance of Put Wall
             if abs(sweep_price - put_wall.strike) < (current_price * 0.005): # 0.5% tolerance
                 valid_sweep = True
                 break
    logger.debug(f"SMC Check: PutWall={put_wall.strike if put_wall else 'None'}, ValidSweep={valid_sweep}, Sweeps={len(recent_sweeps)}")

    # Condition 3: Market Structure Shift (MSS) - Bullish
    # We need to break the LAST High that preceded the sweep
    pivots = smc['structure']['pivots']
    
    mss_confirmed = False
    last_high_pivot = None 
    
    if valid_sweep:
        last_sweep = recent_sweeps[-1]
        sweep_index = last_sweep['index']
        
        # Find the High Pivot immediately BEFORE the sweep
        # We look for pivots with index < sweep_index
        preceding_highs = [p for p in pivots if p['type'] == 'high' and p['index'] < sweep_index]
        
        if preceding_highs:
            last_high_pivot = preceding_highs[-1]
            
            # Check if Price BROKE this high AFTER the sweep
            # We check the max high of candles from sweep_index to now
            # We assume data is sorted by time
            prices_since_sweep = data['close'].iloc[sweep_index:]
            if not prices_since_sweep.empty and prices_since_sweep.max() > last_high_pivot['price']:
                mss_confirmed = True
    
    logger.debug(f"MSS Check: Confirmed={mss_confirmed}, LastHigh={last_high_pivot['price'] if last_high_pivot else 'N/A'}")

    # Condition 4: Re-entry at FVG
    # If MSS recently happened, we look for a Bullish FVG created in the displacement leg
    # Relaxed lookback to 20 bars to allow for pullback time
    recent_fvgs = [f for f in smc['fvgs'] if f['type'] == 'bullish' and f['index'] >= len(data) - 20]
    
    logger.debug(f"FVG Check: Count={len(recent_fvgs)}")
    
    if valid_sweep and mss_confirmed and recent_fvgs:
        # We are simply taking the signal NOW if we are inside the FVG?
        # Or signaling a limit order? The system currently executes 'entries=True' as market orders.
        # For simplicity in V1, we enter on the Close of the MSS candle if valid.
        
        # Refined Entry: Enter if current price is inside a recent FVG OR just on MSS breakout
        best_fvg = recent_fvgs[-1] 
        # Check if we are in buy zone (at FVG or slightly above)
        
        logger.debug(f"Entry Check: Price={current_price}, FVG Top={best_fvg['top']}, Condition={current_price <= best_fvg['top'] * 1.0005}")
        
        if current_price <= best_fvg['top'] * 1.0005: 
             entries.iloc[-1] = True
             bias = "BULLISH"
             reason = f"Bullish Trap & Shift: Sweep of {recent_sweeps[-1]['level']} into Put Wall {put_wall.strike} + MSS."
             stop_loss = recent_sweeps[-1]['level'] - threshold # SL below sweep
             take_profit = call_wall.strike if call_wall else current_price * 1.02

    # --- BEARISH SETUP ---
    # Symetric logic for Call Wall
        
    recent_bull_sweeps = [s for s in smc['liquidity_sweeps'] if s['type'] == 'bearish_sweep' and s['index'] >= len(data) - 10]
    has_bull_sweep = len(recent_bull_sweeps) > 0  # Should be has_bear_sweep really, variable name is confusing
    
    valid_bull_sweep = False # valid_bear_sweep
    if call_wall and has_bull_sweep:
        last_sweep = recent_bull_sweeps[-1]
        if abs(last_sweep['level'] - call_wall.strike) < (threshold * 10):
            valid_bull_sweep = True
            
    last_low_pivot = next((p for p in reversed(pivots) if p['type'] == 'low'), None)
    
    mss_bear_confirmed = False
    if valid_bull_sweep and last_low_pivot:
        if current_price < last_low_pivot['price']:
            mss_bear_confirmed = True
            
    recent_bear_fvgs = [f for f in smc['fvgs'] if f['type'] == 'bearish' and f['index'] >= len(data) - 20]
    
    if valid_bull_sweep and mss_bear_confirmed and recent_bear_fvgs:
        entries.iloc[-1] = True # SHORT is handled by execution engine if direction is SHORT
        bias = "BEARISH"
        reason = f"Bearish Trap & Shift: Sweep of {recent_bull_sweeps[-1]['level']} into Call Wall {call_wall.strike} + MSS."
        stop_loss = recent_bull_sweeps[-1]['level'] + threshold
        take_profit = put_wall.strike if put_wall else current_price * 0.98

    if bias != "NEUTRAL":
        signal_dict = {
            "direction": bias,
            "stop_loss": stop_loss,
            "take_profit": take_profit, 
            "reason": reason,
            "metadata": {
                "put_wall": put_wall.strike if put_wall else None,
                "call_wall": call_wall.strike if call_wall else None,
                "sweep_level": recent_sweeps[-1]['level'] if bias == 'BULLISH' else recent_bull_sweeps[-1]['level'],
                "mss_price": last_high_pivot['price'] if bias == 'BULLISH' else last_low_pivot['price']
            }
        }
        
        # If Bearish, set Exits=True for Long positions? 
        # Strategy interface expects: entries (Open), exits (Close).
        # Depending on engine, entries with direction='SHORT' opens a Short.
        # But if we just return entries=True, we rely on signal_dict['direction'].
        
        if bias == "BEARISH":
            # For simplicity, if we trigger a Short signal, we mark it in entries too?
            # Standard vectorbt usually treats entries as Long Entry.
            # But our execution engine reads signal_dict.
            pass

    return entries, exits, signal_dict
