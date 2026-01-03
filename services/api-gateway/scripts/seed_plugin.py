import sys
import os
# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.plugins import Plugin, PluginCategory
from sqlalchemy import text

def seed_plugin():
    db = SessionLocal()
    try:
        plugins = [
            Plugin(
                id="olympus-lstm-predictor",
                name="Olympus LSTM Predictor",
                description="Uses LSTM model to predict trends based on recent candles.",
                version="1.0.0",
                author="System",
                category=PluginCategory.ALPHA,
                base_config_schema={"mode": "string", "lookback": "integer"}
            ),
            Plugin(
                id="risk-guardrail",
                name="Risk Guardrail (Kernel)",
                description="Blocks trades that exceed defined risk limits.",
                version="1.0.0",
                author="System",
                category=PluginCategory.RISK,
                base_config_schema={"max_risk_per_trade": "number", "blacklist": "array", "mode": "string"}
            )
        ]
    
        for p in plugins:
            existing = db.query(Plugin).filter(Plugin.id == p.id).first()
            if not existing:
                db.add(p)
                print(f"Seeded plugin: {p.name}")
            else:
                print(f"Plugin already exists: {p.name}")
            db.commit() # Commit after each plugin addition or check
    except Exception as e:
        print(f"Error seeding plugin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_plugin()
