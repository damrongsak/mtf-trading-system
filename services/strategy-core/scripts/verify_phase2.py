import asyncio
import json
import logging
from app.quant.positioning import positioning_engine
from app.config_cache import config_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestKelly")

# Mock the cache to return a fake strategy risk profile with Kelly data
fake_strategy_id = "test-kelly-123"
mock_profile = {
    "risk_percentage": 0.02, # 2% default
    "max_risk_usd": 500.0,
    "source": "strategy",
    "historical_metrics": {
        "win_rate": 0.55,
        "profit_factor": 2.0,
        "avg_win": 200.0,
        "avg_loss": 100.0 # stored as positive absolute
    }
}
config_cache.set_config(f"risk_profile_{fake_strategy_id}", mock_profile)

print("--- Testing Kelly Criterion on Mock Data ---")
risk_map = {
    "context": {"regime": "TRENDING"},
    "edge_score": 0.5,
    "layers": {"gamma_bias": "NEUTRAL"}
}

equity = 10000.0
entry_price = 2030.0
stop_loss = 2025.0

result = positioning_engine.calculate_lot_size(
    symbol="XAUUSD",
    entry_price=entry_price,
    stop_loss=stop_loss,
    equity=equity,
    risk_map=risk_map,
    strategy_id=fake_strategy_id
)

print(json.dumps(result, indent=2))
print("Done.")
