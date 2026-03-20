import uuid
import json
import time
import os
import sys
from datetime import datetime

# Add app to sys.path
sys.path.append(os.path.abspath("/app"))

from app.database import SessionLocal
from app.models.signal_log import SignalLog
import redis

# Configuration for demo1
USER_ID = "e2079cc2-11d0-4e8f-9b69-49ea0ba7cd96"
ACCOUNT_ID = "066e21a0-0933-4f70-8e35-605f4759f927"
SYMBOL = "XAUUSD"
TIMEFRAME = "M15"
STRATEGY = "BB_STOCH_OB_v1"

def trigger_simulation():
    db = SessionLocal()
    r = redis.from_url("redis://redis:6379/0")
    
    # Mock current price and ATR for Gold
    current_price = 2155.50
    atr = 5.0
    sl = current_price - (atr * 2) # 2145.50
    tp = current_price + (atr * 4) # 2175.50
    
    # 1. Create PRE-LOGGED Signal
    signal_id = uuid.uuid4()
    signal = SignalLog(
        id=signal_id,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        direction="BULLISH",
        strategy_name=STRATEGY,
        status="CREATED",
        price=current_price,
        reason="BB Lower Bound + Stoch Oversold + OB Confirmation (Simulated)",
        meta_data={
            "sl": sl,
            "tp": tp,
            "simulation": True,
            "indicators": {
                "bb_lower": 2156.0,
                "stoch_k": 15.0,
                "atr": atr
            }
        }
    )
    db.add(signal)
    db.commit()
    print(f"✅ Signal Logged in DB: {signal_id}")

    # 2. Push Execution Command
    client_order_id = str(uuid.uuid4())
    command = {
        "type": "OPEN",
        "symbol": SYMBOL,
        "direction": "BULLISH",
        "volume": 0.01,
        "broker_account_id": ACCOUNT_ID,
        "client_order_id": client_order_id,
        "signal_id": str(signal_id),
        "stop_loss": sl,
        "take_profit": tp,
        "risk_usd": 10.0,
        "pain_threshold": 5000.0,
        "generated_by": STRATEGY,
        "signal_timestamp_ns": time.time_ns(),
        "enqueued_at": time.time()
    }
    
    # The worker looks for 'signal_id' in trace_id field for fill reconciliation? 
    # Actually worker.py:397 says: signal_id=uuid.UUID(data.get("trace_id")) if data.get("trace_id") else None
    # And ctrader.py uses trace_id = context.get("trace_id")
    # And OrderService uses trace_id = req_data.get("client_order_id")
    # Wait, we need the FILL EVENT to carry the Signal ID.
    # In worker.py, message processing for filled orders:
    # 1070: trace_id=trace_id <- this comes from context
    
    # So if I pass client_order_id = signal_id, it will link perfectly.
    # But wait, usually client_order_id is unique per order, and signal_id is per signal.
    # Let's check OrderService again.
    
    r.lpush("queue:execution:commands", json.dumps(command))
    print(f"🚀 Execution Command Pushed to queue:execution:commands")
    print(f"   Client Order ID: {client_order_id}")
    print(f"   Signal ID: {signal_id}")
    
    db.close()

if __name__ == "__main__":
    trigger_simulation()
