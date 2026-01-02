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
        plugin_id = "olympus-lstm-predictor"
        existing = db.query(Plugin).filter(Plugin.id == plugin_id).first()
        if existing:
            print(f"Plugin {plugin_id} already exists.")
            return

        plugin = Plugin(
            id=plugin_id,
            name="Olympus LSTM Predictor",
            description="Predicts next candle close (Mock)",
            version="1.0.0",
            category=PluginCategory.ALPHA,
            base_config_schema={},
            is_system=False
        )
        db.add(plugin)
        db.commit()
        print(f"Successfully seeded plugin {plugin_id}")
    except Exception as e:
        print(f"Error seeding plugin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_plugin()
