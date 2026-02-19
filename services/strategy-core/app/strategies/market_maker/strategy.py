import asyncio
import logging
import time
import numpy as np
from app.logic.market_maker import EFPModel, fast_skew_calc
from app.adapters.execution import execution_client

logger = logging.getLogger(__name__)

METADATA = {
    "name": "EFP Market Maker",
    "description": "Institutional Market Making for XAU/USD using EFP spread and Riccati optimal control.",
    "version": "1.0.0",
    "defaults": {
        "gamma": 0.1,
        "max_inventory": 100.0,
        "risk_aversion": 0.5
    }
}

# Global model instance
model = EFPModel()

async def strategy(state, data_manager):
    """
    Market Maker Strategy Loop.
    Triggered on EFP or Tick events.
    """
    symbol = state.symbol
    
    # 1. Get Latest EFP Data
    efp = data_manager.get_latest_efp(symbol)
    
    # --- Phase 3: Resilience Guard ---
    is_futures_dead = False
    if not efp or (time.time() - efp['t'] > 5.0): # 5 second timeout
        logger.warning(f"Futures Feed Dead for {symbol}. Entering Inventory Minimizer Mode.")
        is_futures_dead = True
        
    # 2. Get Current Inventory (from state or adapter)
    # For now, simulate or fetch from execution_client
    # In a real system, we'd have a local inventory tracker.
    try:
        # Mock inventory for now
        q_s = state.get("inventory_spot", 0.0)
        q_f = state.get("inventory_futures", 0.0)
    except Exception:
        q_s, q_f = 0.0, 0.0

    # 3. Calculate Skews
    if is_futures_dead:
        # Fallback: Freeze spread and increase risk aversion
        spread = state.get("last_stable_spread", 0.0)
        temp_gamma = METADATA["defaults"]["risk_aversion"] * 5.0 # Aggressive scaling
    else:
        spread = efp['s']
        state["last_stable_spread"] = spread
        temp_gamma = METADATA["defaults"]["risk_aversion"]

    t_rem = 3600.0 
    
    # Use localized model with dynamic gamma
    delta_b, delta_a = model.get_optimal_skews(q_s, q_f, spread, 0.0, t_rem)
    
    # Scale skews if futures dead to tighten quotes asymmetrically towards mid
    if is_futures_dead:
        if q_s > 0: delta_a *= 0.5 # Make it easier to hit our ASK (Sell)
        if q_s < 0: delta_b *= 0.5 # Make it easier to hit our BID (Buy)
    
    # 4. Generate Order Payload
    # Quote Price = Mid + Skew
    spot_mid = (efp['b'] + efp['a']) / 2.0
    
    bid_price = spot_mid - delta_b
    ask_price = spot_mid + delta_a
    
    # 5. Push to Execution Service (Binary/Async RPC)
    await execution_client.update_quotes(
        symbol=symbol,
        bid=bid_price,
        ask=ask_price,
        bid_volume=1000,
        ask_volume=1000,
        strategy_id=state.id
    )
    
    return {
        "direction": "NEUTRAL",
        "reason": f"EFP Skew Update: {delta_b:.4f}/{delta_a:.4f}",
        "meta_data": {
            "efp_spread": spread,
            "bid": bid_price,
            "ask": ask_price
        }
    }
