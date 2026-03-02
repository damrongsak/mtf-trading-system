import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from app.analysis.liquidity_profile import LiquidityProfileAnalyzer
from app.models.open_interest import OpenInterest
from app.database import SessionLocal
from app.logic import SignalDirection

logger = logging.getLogger(__name__)

METADATA = {
    "name": "CME Gold OI Breakout Strategy",
    "description": "20-day breakout strategy confirmed by OI change and Max Pain gravity.",
    "defaults": {
        "timeframe": "1h",
        "macro_timeframe": "4h",
        "breakout_period": 120, # 120 * 4H = 20 days
        "oi_change_threshold": 0.05,
        "max_pain_weight": 0.3
    }
}

async def strategy(state, data_manager):
    """
    CME Gold OI Heatmap Strategy:
    1. 20-day Rolling High/Low Breakout (using H4 candles).
    2. OI Change Confirmation (> 5% increase in total OI).
    3. Max Pain proximity filter.
    """
    symbol = state.symbol
    params = state.config_json if state.config_json else METADATA["defaults"]
    
    tf_h1 = "1h"
    tf_h4 = "4h"
    
    # FETCH DATA
    candles_h1 = data_manager.get_candles(symbol, timeframe=tf_h1)
    candles_h4 = data_manager.get_candles(symbol, timeframe=tf_h4)
    
    if candles_h1.empty or candles_h4.empty or len(candles_h4) < params["breakout_period"]:
        return None, None, None, []

    current_price = candles_h1['close'].iloc[-1]
    
    # 1. BREAKOUT LOGIC (20-day High/Low)
    h4_period = params["breakout_period"]
    upper_band = candles_h4['high'].shift(1).rolling(window=h4_period).max().iloc[-1]
    lower_band = candles_h4['low'].shift(1).rolling(window=h4_period).min().iloc[-1]
    
    is_breakout_up = current_price > upper_band
    is_breakout_down = current_price < lower_band
    
    if not (is_breakout_up or is_breakout_down):
        return None, None, None, []

    # 2. OI CONFIRMATION
    # We need the latest 2 snapshots to check for change
    snapshots = fetch_last_two_oi_snapshots()
    if not snapshots or len(snapshots) < 2:
        return None, None, None, []
    
    latest_oi = snapshots[0]['total_oi']
    prev_oi = snapshots[1]['total_oi']
    oi_change = (latest_oi - prev_oi) / prev_oi if prev_oi > 0 else 0
    
    if oi_change < params["oi_change_threshold"]:
        return None, None, None, []

    # 3. MAX PAIN FILTER
    analyzer = LiquidityProfileAnalyzer()
    analysis = analyzer.analyze_snapshot(snapshots[0]['records'], current_spot_price=current_price)
    max_pain = analysis.get('max_pain')
    
    # If breaking out UP, we want Max Pain to be above current price (pulling it higher)
    # or at least not far below.
    # If breaking out DOWN, we want Max Pain to be below.
    direction = None
    reason = ""
    
    if is_breakout_up and oi_change > params["oi_change_threshold"]:
        direction = "BULLISH"
        reason = f"20-day Bullish Breakout for {snapshots[0]['active_contract']} with {oi_change:.1%} OI Increase. Max Pain at {max_pain}"
    elif is_breakout_down and oi_change > params["oi_change_threshold"]:
        direction = "BEARISH"
        reason = f"20-day Bearish Breakout for {snapshots[0]['active_contract']} with {oi_change:.1%} OI Increase. Max Pain at {max_pain}"

    if not direction:
        return None, None, None, []

    # SIGNAL OUTPUT
    entries = pd.Series(False, index=candles_h1.index)
    exits = pd.Series(False, index=candles_h1.index)
    
    entries.iloc[-1] = (direction == "BULLISH")
    exits.iloc[-1] = (direction == "BEARISH")
    
    signal_dict = {
        "symbol": symbol,
        "direction": direction,
        "price": float(current_price),
        "reason": reason,
        "metadata": {
            "oi_change": oi_change,
            "max_pain": max_pain,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "heatmap_snippet": analysis.get('heatmap', [])[:5]
        }
    }

    logs = [
        f"CME OI Breakout | Direction: {direction} | Price: {current_price:.2f} | OI Change: {oi_change:.1%} | Max Pain: {max_pain}"
    ]
    
    return entries, exits, signal_dict, logs

def fetch_last_two_oi_snapshots():
    db = SessionLocal()
    try:
        # Get last 2 snapshot times
        times = db.query(OpenInterest.snapshot_at).distinct().order_by(OpenInterest.snapshot_at.desc()).limit(2).all()
        if len(times) < 2: return []
        
        results = []
        for t in times:
            snapshot_at = t[0]
            # Fetch records and group them by contract
            records = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_at).all()
            
            # Find the active contract for this snapshot via total OI
            df_snapshot = pd.DataFrame([{
                'contract_symbol': r.contract_symbol,
                'call_oi': float(r.call_oi or 0),
                'put_oi': float(r.put_oi or 0)
            } for r in records])
            
            if df_snapshot.empty: continue
            
            active_contract = df_snapshot.groupby('contract_symbol').apply(lambda x: (x['call_oi'] + x['put_oi']).sum()).idxmax()
            active_records = [r for r in records if r.contract_symbol == active_contract]
            total_oi = sum([float(r.call_oi or 0) + float(r.put_oi or 0) for r in active_records])
            
            # Convert to analyzer format
            rec_dicts = []
            for r in active_records:
                rec_dicts.append({
                    'strike': float(r.strike),
                    'call_oi': float(r.call_oi or 0),
                    'put_oi': float(r.put_oi or 0),
                    'contract_symbol': r.contract_symbol,
                    'underlying_price': float(r.underlying_price) if r.underlying_price else None,
                    'dte': r.dte
                })
                
            results.append({
                'snapshot_at': snapshot_at,
                'active_contract': active_contract,
                'total_oi': total_oi,
                'records': rec_dicts
            })
        return results
    except Exception as e:
        logger.error(f"Error fetching last two OI snapshots: {e}")
        return []
    finally:
        db.close()
